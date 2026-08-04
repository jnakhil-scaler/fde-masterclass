from app.models import Product, ProductVariant, Customer, Order, OrderItem, Invoice, CreditLedger, Supplier, SupplierRateCard, WhatsappMessage


def test_can_create_product_and_query_it(db):
    product = Product(name="Ambuja Cement", brand="Ambuja", category="Cement", unit="bag", hsn_code="2523", current_stock=340)
    db.add(product)
    db.commit()

    fetched = db.query(Product).filter_by(name="Ambuja Cement").first()
    assert fetched.current_stock == 340


def test_order_links_to_customer_and_items(db):
    customer = Customer(name="Vinod Builders", phone="9000000000", area="Indore")
    db.add(customer)
    db.commit()

    product = Product(name="TMT Sariya 10mm", brand="Generic", category="Steel", unit="ton", hsn_code="7213", current_stock=10)
    db.add(product)
    db.commit()

    order = Order(customer_id=customer.id, source="whatsapp", delivery_address="Sharma site", delivery_time="tomorrow morning")
    order.items.append(OrderItem(product_id=product.id, qty=2, unit_price=45000))
    db.add(order)
    db.commit()

    fetched = db.query(Order).filter_by(customer_id=customer.id).first()
    assert len(fetched.items) == 1
    assert fetched.items[0].qty == 2


def test_product_variant_links_raw_names_to_normalized_product(db):
    product = Product(name="Ambuja Cement", brand="Ambuja", category="Cement", unit="bag", hsn_code="2523", current_stock=340)
    db.add(product)
    db.commit()

    db.add(ProductVariant(raw_name="ambuja cem. (50 KG)", product_id=product.id))
    db.add(ProductVariant(raw_name="AMBUJA CEMENT 50KG", product_id=product.id))
    db.add(ProductVariant(raw_name="Ambuja Cement 50kg", product_id=product.id))
    db.commit()

    fetched = db.query(ProductVariant).filter_by(product_id=product.id).all()
    raw_names = {variant.raw_name for variant in fetched}
    assert raw_names == {"ambuja cem. (50 KG)", "AMBUJA CEMENT 50KG", "Ambuja Cement 50kg"}


def test_order_total_amount_persists(db):
    customer = Customer(name="Vinod Builders", phone="9000000000", area="Indore")
    db.add(customer)
    db.commit()

    order = Order(customer_id=customer.id, source="whatsapp", total_amount=760000)
    db.add(order)
    db.commit()

    fetched = db.query(Order).filter_by(customer_id=customer.id).first()
    assert fetched.total_amount == 760000


def test_whatsapp_message_stores_raw_metadata_as_jsonb(db):
    msg = WhatsappMessage(raw_text="bhai 50 bag cem chahiye", raw_metadata={"is_voice_note": False})
    db.add(msg)
    db.commit()

    fetched = db.query(WhatsappMessage).first()
    assert fetched.raw_metadata["is_voice_note"] is False
