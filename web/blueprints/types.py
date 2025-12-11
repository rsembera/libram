# -*- coding: utf-8 -*-
"""
Libram Book Types Blueprint
Handles book type management (CRUD operations)
"""

from flask import Blueprint, render_template, request, redirect, url_for, jsonify, current_app

# Initialize blueprint
types_bp = Blueprint('types', __name__)


# Color palette for book types
COLOR_PALETTE = [
    {'hex': '#9FCFC0', 'name': 'Seafoam', 'bubble': '#E0F2EE'},
    {'hex': '#B8D4E8', 'name': 'Sky', 'bubble': '#EBF3FA'},
    {'hex': '#D4C5E0', 'name': 'Wisteria', 'bubble': '#F3EDF7'},
    {'hex': '#C8E6C9', 'name': 'Mint', 'bubble': '#EDF7ED'},
    {'hex': '#FFE0B2', 'name': 'Peach', 'bubble': '#FFF5E6'},
    {'hex': '#F8BBD0', 'name': 'Blush', 'bubble': '#FEEEF3'},
    {'hex': '#D7CCC8', 'name': 'Stone', 'bubble': '#F2EFEE'},
    {'hex': '#CFD8DC', 'name': 'Slate', 'bubble': '#EEF1F3'},
    {'hex': '#E1BEE7', 'name': 'Orchid', 'bubble': '#F7EFF9'},
]


@types_bp.route('/types')
def manage_types():
    """Display book types management page."""
    db = current_app.get_db()
    all_types = db.get_all_book_types()
    
    # Add book count to each type
    for t in all_types:
        t['book_count'] = db.get_books_count_by_type(t['id'])
    
    return render_template('manage_types.html', types=all_types)


@types_bp.route('/types/add', methods=['GET', 'POST'])
def add_type():
    """Add a new book type."""
    db = current_app.get_db()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()[:9]  # 9 char limit
        color = request.form.get('color', '#9FCFC0')
        bubble_color = request.form.get('bubble_color', '#E0F2EE')
        
        if name:
            try:
                db.add_book_type(name, color, bubble_color)
                return redirect(url_for('types.manage_types'))
            except Exception as e:
                error = "A type with that name already exists." if "UNIQUE" in str(e) else str(e)
                return render_template('add_edit_type.html', type=None, colors=COLOR_PALETTE, error=error)
        
    return render_template('add_edit_type.html', type=None, colors=COLOR_PALETTE)


@types_bp.route('/types/<int:type_id>/edit', methods=['GET', 'POST'])
def edit_type(type_id):
    """Edit an existing book type."""
    db = current_app.get_db()
    type_obj = db.get_book_type(type_id)
    
    if not type_obj:
        return redirect(url_for('types.manage_types'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()[:9]
        color = request.form.get('color')
        bubble_color = request.form.get('bubble_color')
        
        if name:
            try:
                db.update_book_type(type_id, name=name, color=color, bubble_color=bubble_color)
                return redirect(url_for('types.manage_types'))
            except Exception as e:
                error = "A type with that name already exists." if "UNIQUE" in str(e) else str(e)
                return render_template('add_edit_type.html', type=type_obj, colors=COLOR_PALETTE, error=error)
    
    return render_template('add_edit_type.html', type=type_obj, colors=COLOR_PALETTE)


@types_bp.route('/types/<int:type_id>/delete', methods=['POST'])
def delete_type(type_id):
    """Delete a book type."""
    db = current_app.get_db()
    type_obj = db.get_book_type(type_id)
    
    if not type_obj:
        return jsonify({'success': False, 'error': 'Type not found'}), 404
    
    # Check book count
    book_count = db.get_books_count_by_type(type_id)
    if book_count > 0:
        return jsonify({
            'success': False,
            'error': f'Cannot delete: {book_count} book(s) are assigned to this type'
        }), 400
    
    # Check if last type
    all_types = db.get_all_book_types()
    if len(all_types) <= 1:
        return jsonify({
            'success': False,
            'error': 'Cannot delete: At least one book type must exist'
        }), 400
    
    success = db.delete_book_type(type_id)
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Database error'}), 500


@types_bp.route('/api/book-types')
def get_types_api():
    """API endpoint to get all book types."""
    db = current_app.get_db()
    types = db.get_all_book_types()
    return jsonify(types)
