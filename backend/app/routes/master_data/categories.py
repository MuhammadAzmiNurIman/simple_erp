# app/routes/categories.py
# CRUD Kategori - Master Data Kategori
from flask import Blueprint, current_app, request, jsonify
from app import db, ma
from app.models import Category
from app.schemas import category_schema, categories_schema

bp = Blueprint('categories', __name__)


@bp.route('/categories', methods=['GET'])
def get_categories():
    """Get all categories with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    active_only = request.args.get('active', 'true', type=str).lower() == 'true'

    query = Category.query

    if active_only:
        query = query.filter_by(is_active=True)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    categories = pagination.items

    return jsonify({
        'data': categories_schema.dump(categories),
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    })


@bp.route('/categories', methods=['POST'])
def create_category():
    """Create new category"""
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400
    name = data.get('name')
    description = data.get('description', '')

    if not name:
        return jsonify({'error': 'Name is required'}), 400

    # Check if category already exists
    existing = Category.query.filter_by(name=name).first()
    if existing:
        return jsonify({'error': 'Category name already exists'}), 409

    category = Category(name=name, description=description)
    try:
        db.session.add(category)
        db.session.commit()

        return jsonify({
            'message': 'Category created successfully',
            'data': category_schema.dump(category)
        }), 201
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Category creation failed')
        return jsonify({'error': 'Unable to create category'}), 500


@bp.route('/categories/<int:category_id>', methods=['GET'])
def get_category(category_id):
    """Get single category"""
    category = db.get_or_404(Category, category_id)
    return jsonify({
        'data': category_schema.dump(category)
    })


@bp.route('/categories/<int:category_id>', methods=['PATCH'])
def update_category(category_id):
    """Update category"""
    category = db.get_or_404(Category, category_id)
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400
    if 'name' in data:
        # Check if new name conflicts
        existing = Category.query.filter(
            Category.name == data['name'], 
            Category.id != category_id
        ).first()
        if existing:
            return jsonify({'error': 'Category name already exists'}), 409
        category.name = data['name']
    if 'description' in data:
        category.description = data['description']
    try:
        db.session.commit()
        return jsonify({
            'message': 'Category updated successfully',
            'data': category_schema.dump(category)
        })
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Category update failed')
        return jsonify({'error': 'Unable to update category'}), 500


@bp.route('/categories/<int:category_id>', methods=['DELETE'])
def delete_category(category_id):
    """Soft delete category (set inactive)"""
    category = db.get_or_404(Category, category_id)
    try:
        category.is_active = False
        db.session.commit()
        return jsonify({'message': 'Category deactivated successfully'})
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Category deactivation failed')
        return jsonify({'error': 'Unable to deactivate category'}), 500