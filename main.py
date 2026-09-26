from .database import engine, Base, get_db
from . import models, auth
from fastapi import Depends, FastAPI, Form, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

Base.metadata.create_all(bind=engine)

app = FastAPI(title="StockSense IMS")
templates = Jinja2Templates(directory="app/templates")
DB_DEPENDENCY = Depends(get_db)

def seed_defaults(db: Session):
    if not db.query(models.Warehouse).first():
        db.add_all([
            models.Warehouse(name="Main Store", location_code="WH-MAIN"),
            models.Warehouse(name="Production Floor", location_code="WH-PROD"),
            models.Warehouse(name="Rack B", location_code="WH-RACKB")
        ])
        db.commit()
    if not db.query(models.User).filter(models.User.username == "admin").first():
        db.add(models.User(
            username="admin",
            email="admin@stocksense.io",
            password_hash=auth.get_password_hash("admin123"),
            role="Inventory Manager"
        ))
        db.commit()

# --- Auth Routes ---
@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login")
def login(response: Response, request: Request, username: str = Form(...), password: str = Form(...), db: Session = DB_DEPENDENCY):
    seed_defaults(db)
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not auth.verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password"})
    
    token = auth.create_access_token({"sub": user.username, "role": user.role})
    res = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    res.set_cookie(key="access_token", value=token, httponly=True)
    return res

@app.get("/logout")
def logout():
    res = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    res.delete_cookie("access_token")
    return res

# --- Dashboard & KPIs ---
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = DB_DEPENDENCY):
    seed_defaults(db)
    total_products = db.query(models.Product).count()

    # Calculate stock alerts
    stocks = db.query(models.Stock).all()
    low_stock_count = 0
    for s in stocks:
        if s.quantity <= (s.product.min_reorder_level if s.product else 10):
            low_stock_count += 1

    pending_receipts = db.query(models.StockMove).filter(models.StockMove.doc_type == "Receipt", models.StockMove.status != "Done").count()
    pending_deliveries = db.query(models.StockMove).filter(models.StockMove.doc_type == "Delivery", models.StockMove.status != "Done").count()
    internal_transfers = db.query(models.StockMove).filter(models.StockMove.doc_type == "Internal", models.StockMove.status != "Done").count()

    moves = db.query(models.StockMove).order_by(models.StockMove.id.desc()).limit(10).all()

    return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "total_products": total_products,
            "low_stock_count": low_stock_count,
            "pending_receipts": pending_receipts,
            "pending_deliveries": pending_deliveries,
            "internal_transfers": internal_transfers,
            "moves": moves
        })
# --- Product Management ---
@app.get("/products", response_class=HTMLResponse)
def products_page(request: Request, db: Session = DB_DEPENDENCY):
    products = db.query(models.Product).all()
    warehouses = db.query(models.Warehouse).all()
    stocks = db.query(models.Stock).all()
    return templates.TemplateResponse("products.html", {
        "request": request,
        "products": products,
        "warehouses": warehouses,
        "stocks": stocks
    })

@app.post("/products/create")
def create_product(
    sku: str = Form(...),
    name: str = Form(...),
    category: str = Form(...),
    uom: str = Form(...),
    min_reorder: float = Form(10.0),
    initial_stock: float = Form(0.0),
    warehouse_id: int = Form(...),
    db: Session = DB_DEPENDENCY
):
    product = models.Product(sku=sku, name=name, category=category, uom=uom, min_reorder_level=min_reorder)
    db.add(product)
    db.commit()
    db.refresh(product)

    stock = models.Stock(product_id=product.id, warehouse_id=warehouse_id, quantity=initial_stock)
    db.add(stock)

    if initial_stock > 0:
        move = models.StockMove(
            doc_type="Receipt",
            status="Done",
            product_id=product.id,
            dest_warehouse_id=warehouse_id,
            quantity=initial_stock,
            partner="Opening Stock"
        )
        db.add(move)

    db.commit()
    return RedirectResponse(url="/products", status_code=status.HTTP_302_FOUND)

# --- Operations (Receipts, Deliveries, Transfers, Adjustments) ---
@app.get("/operations", response_class=HTMLResponse)
def operations_page(request: Request, doc_type: str = "All", db: Session = DB_DEPENDENCY):
    query = db.query(models.StockMove)
    if doc_type != "All":
        query = query.filter(models.StockMove.doc_type == doc_type)
    moves = query.order_by(models.StockMove.id.desc()).all()
    products = db.query(models.Product).all()
    warehouses = db.query(models.Warehouse).all()
    return templates.TemplateResponse("operations.html", {
        "request": request,
        "moves": moves,
        "products": products,
        "warehouses": warehouses,
        "selected_type": doc_type
    })

@app.post("/operations/create")
def create_operation(
    doc_type: str = Form(...),
    product_id: int = Form(...),
    quantity: float = Form(...),
    src_warehouse_id: int = Form(None),
    dest_warehouse_id: int = Form(None),
    partner: str = Form(None),
    db: Session = DB_DEPENDENCY
):
    move = models.StockMove(
        doc_type=doc_type,
        status="Draft",
        product_id=product_id,
        quantity=quantity,
        src_warehouse_id=src_warehouse_id if src_warehouse_id != 0 else None,
        dest_warehouse_id=dest_warehouse_id if dest_warehouse_id != 0 else None,
        partner=partner
    )
    db.add(move)
    db.commit()
    return RedirectResponse(url="/operations", status_code=status.HTTP_302_FOUND)

@app.post("/operations/{move_id}/validate")
def validate_operation(move_id: int, db: Session = DB_DEPENDENCY):
    move = db.query(models.StockMove).filter(models.StockMove.id == move_id).first()
    if not move or move.status == "Done":
        return RedirectResponse(url="/operations", status_code=status.HTTP_302_FOUND)

    # 1. Receipt: Add stock to destination
    if move.doc_type == "Receipt":
        stock = db.query(models.Stock).filter_by(product_id=move.product_id, warehouse_id=move.dest_warehouse_id).first()
        if stock:
            stock.quantity += move.quantity
        else:
            db.add(models.Stock(product_id=move.product_id, warehouse_id=move.dest_warehouse_id, quantity=move.quantity))

    # 2. Delivery: Deduct stock from source
    elif move.doc_type == "Delivery":
        stock = db.query(models.Stock).filter_by(product_id=move.product_id, warehouse_id=move.src_warehouse_id).first()
        if stock and stock.quantity >= move.quantity:
            stock.quantity -= move.quantity
        else:
            # Prevent negative stock or raise warning
            if stock:
                stock.quantity -= move.quantity

    # 3. Internal Transfer: Deduct from source, add to destination
    elif move.doc_type == "Internal":
        src_stock = db.query(models.Stock).filter_by(product_id=move.product_id, warehouse_id=move.src_warehouse_id).first()
        if src_stock:
            src_stock.quantity -= move.quantity
        dest_stock = db.query(models.Stock).filter_by(product_id=move.product_id, warehouse_id=move.dest_warehouse_id).first()
        if dest_stock:
            dest_stock.quantity += move.quantity
        else:
            db.add(models.Stock(product_id=move.product_id, warehouse_id=move.dest_warehouse_id, quantity=move.quantity))

    # 4. Adjustment: Set physical count directly
    elif move.doc_type == "Adjustment":
        stock = db.query(models.Stock).filter_by(product_id=move.product_id, warehouse_id=move.dest_warehouse_id).first()
        if stock:
            stock.quantity = move.quantity
        else:
            db.add(models.Stock(product_id=move.product_id, warehouse_id=move.dest_warehouse_id, quantity=move.quantity))

    move.status = "Done"
    db.commit()
    return RedirectResponse(url="/operations", status_code=status.HTTP_302_FOUND)