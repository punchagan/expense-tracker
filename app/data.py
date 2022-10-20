from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.model import Category, Tag
from app.util import DB_NAME, delta_percent, format_month, get_db_url

CATEGORIES = [
    "Automobile",
    "Charity",
    "Clothes",
    "Doctor Consultation",
    "Earned Interest",
    "Eating Out",
    "Education",
    "Electronic Gadgets",
    "Entertainment",
    "Fuel",
    "Gift",
    "Groceries",
    "Gym",
    "Health Insurance",
    "Housing",
    "Investment",
    "Medication",
    "Personal Care",
    "Public Transit",
    "Salary",
    "Shoes",
    "Sports",
    "Takeaway",
    "Travel",
    "Utilities",
]


def create_categories(session, categories):
    categories = sorted(set(categories))
    all_categories = session.query(Category).all()
    all_names = {cat.name for cat in all_categories}
    # Add new categories
    objects = [Category(name=name) for name in categories if name not in all_names]
    session.bulk_save_objects(objects)
    # Delete removed categories
    for category in all_categories:
        if category.name not in categories:
            session.delete(category)
    session.commit()


def create_tags(session, tags):
    tags = sorted(set(tags))
    all_tags = session.query(Tag).all()
    all_names = {tag.name for tag in all_tags}
    # Add new tags
    objects = [Tag(name=name) for name in tags if name not in all_names]
    session.bulk_save_objects(objects)
    # Delete removed tags
    for tag in all_tags:
        if tag.name not in tags:
            session.delete(tag)
    session.commit()
