from datetime import datetime, timezone

from marshmallow import Schema, fields


# --- 1. Define Schemas ---

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
    status = fields.Str(required=True)  # Draft, Waiting, Ready, Done, Canceled
    created_at = fields.DateTime(required=True)

    # Nested schemas
    product = fields.Nested(ProductResponseSchema, allow_none=True)
    src_warehouse = fields.Nested(WarehouseResponseSchema, allow_none=True)
    dest_warehouse = fields.Nested(WarehouseResponseSchema, allow_none=True)


# --- 2. Instantiate Schemas ---

stock_move_schema = StockMoveResponseSchema()


# --- 3. Test & Demonstration ---

if __name__ == "__main__":
    # Sample data (simulating data coming from a database or API)
    sample_data = {
        "id": 101,
        "status": "Ready",
        "quantity": 25.5,
        "created_at": datetime.now(timezone.utc).isoformat(),
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
            "location": "Mall Branch"
        }
    }

    # Validate and load data
    validated_move = stock_move_schema.load(sample_data)
    print("Successfully validated and loaded data:")
    print(validated_move)

    # Dump data back to JSON-friendly dictionary
    dumped_json = stock_move_schema.dump(validated_move)
    print("\nSerialized Output:")
    print(dumped_json)