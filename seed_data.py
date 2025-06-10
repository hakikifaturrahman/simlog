import json
from datetime import datetime
from app import app, db
from models import User, Product, Supplier, Order, Shipment, FinancialRecord, SupplierTransaction

def seed_data():
    with app.app_context():
        print("Seeding database...")

        # Helper untuk konversi tanggal dari format ISO
        def parse_date(date_str):
            if not date_str:
                return None
            # Mengganti 'Z' dengan '+00:00' agar bisa diparsing oleh fromisoformat
            if date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'
            return datetime.fromisoformat(date_str)

        # 1. Users
        with open('DB/users.json') as f:
            users_data = json.load(f)
            for u in users_data:
                if not User.query.get(u['id']):
                    new_user = User(
                        id=u['id'],
                        username=u['username'],
                        email=u['email'],
                        password_hash=u['password_hash'],
                        role=u['role'],
                        created_at=parse_date(u['created_at'])
                    )
                    db.session.add(new_user)

        # 2. Products
        with open('DB/products.json') as f:
            products_data = json.load(f)
            for p in products_data:
                 if not Product.query.get(p['id']):
                    new_product = Product(
                        id=p['id'], name=p['name'], description=p['description'],
                        stock_quantity=p['stock_quantity'], min_stock_level=p['min_stock_level'],
                        unit_price=p['unit_price'], created_at=parse_date(p['created_at']),
                        updated_at=parse_date(p['updated_at'])
                    )
                    db.session.add(new_product)

        # 3. Suppliers
        with open('DB/suppliers.json') as f:
            suppliers_data = json.load(f)
            for s in suppliers_data:
                if not Supplier.query.get(s['id']):
                    new_supplier = Supplier(
                        id=s['id'], name=s['name'], contact_person=s['contact_person'],
                        email=s['email'], phone=s['phone'], address=s['address'],
                        rating=s['rating'], created_at=parse_date(s['created_at'])
                    )
                    db.session.add(new_supplier)

        db.session.commit() # Commit setelah user, product, supplier dibuat

        # 4. Orders
        with open('DB/orders.json') as f:
            orders_data = json.load(f)
            for o in orders_data:
                if not Order.query.get(o['id']):
                    new_order = Order(
                        id=o['id'], user_id=o['user_id'], supplier_id=o['supplier_id'],
                        product_id=o['product_id'], quantity=o['quantity'], unit_price=o['unit_price'],
                        total_cost=o['total_cost'], logistics_cost=o['logistics_cost'],
                        package_type=o['package_type'], status=o['status'],
                        order_date=parse_date(o['order_date'])
                    )
                    db.session.add(new_order)

        # 5. Shipments
        with open('DB/shipments.json') as f:
            shipments_data = json.load(f)
            for s in shipments_data:
                if not Shipment.query.get(s['id']):
                    new_shipment = Shipment(
                        id=s['id'], order_id=s['order_id'], tracking_number=s['tracking_number'],
                        status=s['status'], shipped_date=parse_date(s['shipped_date']),
                        estimated_delivery=parse_date(s['estimated_delivery']),
                        actual_delivery=parse_date(s['actual_delivery']), current_location=s['current_location']
                    )
                    db.session.add(new_shipment)

        # 6. Financial Records
        with open('DB/financial_records.json') as f:
            records_data = json.load(f)
            for r in records_data:
                if not FinancialRecord.query.get(r['id']):
                    new_record = FinancialRecord(
                        id=r['id'], order_id=r['order_id'], transaction_type=r['transaction_type'],
                        amount=r['amount'], description=r['description'],
                        transaction_date=parse_date(r['transaction_date'])
                    )
                    db.session.add(new_record)

        # 7. Supplier Transactions
        with open('DB/supplier_transactions.json') as f:
            trans_data = json.load(f)
            for t in trans_data:
                if not SupplierTransaction.query.get(t['id']):
                    new_tran = SupplierTransaction(
                        id=t['id'], supplier_id=t['supplier_id'], order_id=t['order_id'],
                        amount=t['amount'], transaction_date=parse_date(t['transaction_date'])
                    )
                    db.session.add(new_tran)

        db.session.commit()
        print("Database seeded successfully.")

if __name__ == "__main__":
    seed_data()