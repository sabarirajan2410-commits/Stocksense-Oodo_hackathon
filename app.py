from datetime import datetime, timezone
from flask import Flask, jsonify, render_template_string
from marshmallow import Schema, fields

app = Flask(__name__)

# --- Marshmallow Schemas ---

class ProductResponseSchema(Schema):
    id = fields.Int(required=True)
    name = fields.Str(required=True)
    sku = fields.Str(allow_none=True)

class WarehouseResponseSchema(Schema):
    id = fields.Int(required=True)
    name = fields.Str(required=True)
    location = fields.Str(allow_none=True)

class StockMoveBaseSchema(Schema):
    quantity = fields.Float(load_default=0.0, dump_default=0.0)

class StockMoveResponseSchema(StockMoveBaseSchema):
    id = fields.Int(required=True)
    status = fields.Str(required=True)
    created_at = fields.DateTime(required=True)
    product = fields.Nested(ProductResponseSchema, allow_none=True)
    src_warehouse = fields.Nested(WarehouseResponseSchema, allow_none=True)
    dest_warehouse = fields.Nested(WarehouseResponseSchema, allow_none=True)

stock_move_schema = StockMoveResponseSchema()

# --- Sample Data ---
sample_stock_move = {
    "id": 101,
    "status": "Ready",
    "quantity": 25.0,
    "created_at": datetime.now(timezone.utc),
    "product": {
        "id": 1,
        "name": "Mechanical Keyboard",
        "sku": "KB-101"
    },
    "src_warehouse": {
        "id": 10,
        "name": "Central Hub",
        "location": "Warehouse A"
    },
    "dest_warehouse": {
        "id": 20,
        "name": "Retail Store",
        "location": "Floor 2"
    }
}

# --- HTML Template for the Browser ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Stock Move Details</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f8fafc; padding: 40px; color: #1e293b; }
        .card { max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); padding: 24px; }
        h1 { margin-top: 0; font-size: 22px; color: #0f172a; border-bottom: 2px solid #f1f5f9; padding-bottom: 12px; }
        .badge { display: inline-block; padding: 4px 10px; border-radius: 9999px; font-size: 12px; font-weight: 600; background: #dcfce7; color: #15803d; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 20px; }
        .box { background: #f8fafc; padding: 12px; border-radius: 8px; border: 1px solid #e2e8f0; }
        .label { font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: bold; margin-bottom: 4px; }
        .value { font-size: 15px; font-weight: 500; }
        .route { margin-top: 20px; padding: 16px; background: #eff6ff; border-radius: 8px; border: 1px solid #bfdbfe; font-size: 14px; }
    </style>
</head>
<body>
    <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h1>Stock Move #{{ data.id }}</h1>
            <span class="badge">{{ data.status }}</span>
        </div>
        
        <p><strong>Created:</strong> {{ data.created_at }}</p>

        <div class="grid">
            <div class="box">
                <div class="label">Product</div>
                <div class="value">{{ data.product.name if data.product else 'N/A' }}</div>
                <small style="color: #64748b;">SKU: {{ data.product.sku if data.product else 'N/A' }}</small>
            </div>
            <div class="box">
                <div class="label">Quantity</div>
                <div class="value">{{ data.quantity }} units</div>
            </div>
        </div>

        <div class="route">
            <strong>Route:</strong> 
            {{ data.src_warehouse.name if data.src_warehouse else 'None' }} 
            &rarr; 
            {{ data.dest_warehouse.name if data.dest_warehouse else 'None' }}
        </div>
    </div>
</body>
</html>
"""

# --- Web Routes ---

# 1. UI Page Route (Opens in browser)
@app.route("/")
def home():
    # Serialize data using Marshmallow
    validated_data = stock_move_schema.dump(sample_stock_move)
    return render_template_string(HTML_TEMPLATE, data=validated_data)

# 2. Raw JSON API Route
@app.route("/api/move")
def get_move_json():
    validated_data = stock_move_schema.dump(sample_stock_move)
    return jsonify(validated_data)

if __name__ == "__main__":
    app.run(debug=True, port=5000)