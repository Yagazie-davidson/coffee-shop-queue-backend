from flask import Flask, request, jsonify
from flask_cors import CORS
from queue_manager import QueueManager, Priority
from datetime import datetime
import os
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

allowed_origins = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
if os.environ.get('RENDER_ENVIRONMENT'):
    cors_origins = [allowed_origins, "https://*.render.com", "https://*.up.render.com", "https://*.vercel.app"]
else:
    # In development, use localhost
    cors_origins = "http://localhost:3000"

CORS(app, resources={r"/*": {"origins": cors_origins}})

# Global queue manager instance
queue_manager = QueueManager()

# Simple caching for efficient polling
cache = {
    'last_update': time.time(),
    'queue_status': None,
    'analytics': None,
    'version': 0
}

def update_cache():
    """Update cache with latest data and increment version"""
    cache
    cache['last_update'] = time.time()
    cache['queue_status'] = queue_manager.get_queue_status()
    cache['analytics'] = queue_manager.get_analytics()
    cache['version'] += 1
    return cache['version']

# API Routes
@app.route('/api/orders', methods=['POST'])
def create_order():
    """Create a new order"""
    try:
        data = request.get_json()
        customer_name = data.get('customer_name')
        items = data.get('items', [])
        priority_str = data.get('priority', 'REGULAR')
        
        if not customer_name or not items:
            return jsonify({'error': 'Customer name and items are required'}), 400
        
        # Convert priority string to enum
        try:
            priority = Priority[priority_str.upper()]
        except KeyError:
            priority = Priority.REGULAR
        
        order = queue_manager.add_order(customer_name, items, priority)
        
        # Update cache for polling clients
        update_cache()
        
        return jsonify({
            'success': True,
            'order': order.to_dict(),
            'message': f'Order created! You are #{order.position_in_queue} in queue'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders/next', methods=['POST'])
def get_next_order():
    """Get the next order for preparation (staff only)"""
    try:
        order = queue_manager.get_next_order()
        
        if not order:
            return jsonify({'message': 'No orders in queue'}), 204
        
        # Update cache for polling clients
        update_cache()
        
        return jsonify({
            'success': True,
            'order': order.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders/<order_id>/complete', methods=['POST'])
def complete_order(order_id):
    """Mark an order as completed"""
    try:
        success = queue_manager.complete_order(order_id)
        
        if not success:
            return jsonify({'error': 'Order not found or not in preparation'}), 404
        
        # Update cache for polling clients
        update_cache()
        
        return jsonify({'success': True, 'message': 'Order completed'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders/<order_id>/cancel', methods=['DELETE'])
def cancel_order(order_id):
    """Cancel an order"""
    try:
        success = queue_manager.cancel_order(order_id)
        
        if not success:
            return jsonify({'error': 'Order not found'}), 404
        
        # Update cache for polling clients
        update_cache()
        
        return jsonify({'success': True, 'message': 'Order cancelled'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/queue/poll', methods=['GET'])
def poll_queue_updates():
    """Polling endpoint for real-time updates"""
    try:
        # Check if client wants only updates since last version
        client_version = request.args.get('version', 0, type=int)
        
        # If client has latest version, return 304 Not Modified
        if client_version >= cache['version']:
            return jsonify({'status': 'no_change'}), 304
        
        return jsonify({
            'queue_status': cache['queue_status'],
            'analytics': cache['analytics'],
            'version': cache['version'],
            'timestamp': datetime.now().isoformat(),
            'last_update': cache['last_update']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/queue/status', methods=['GET'])
def get_queue_status():
    """Get current queue status (always fresh data)"""
    try:
        status = queue_manager.get_queue_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# @app.route('/api/analytics', methods=['GET'])
# def get_analytics():
#     """Get queue analytics (always fresh data)"""
#     try:
#         analytics = queue_manager.get_analytics()
#         return jsonify(analytics)
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

@app.route('/api/updates', methods=['GET'])
def get_updates():
    """Get all updates in one request (optimized for polling)"""
    try:
        client_version = request.args.get('version', 0, type=int)
        
        # If client has latest version, return 304 Not Modified
        if client_version >= cache['version']:
            return jsonify({'status': 'no_change'}), 304
        
        return jsonify({
            'queue_status': cache['queue_status'],
            'analytics': cache['analytics'],
            'version': cache['version'],
            'timestamp': datetime.now().isoformat(),
            'last_update': cache['last_update']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/customer/<customer_name>/orders', methods=['GET'])
def get_customer_orders(customer_name):
    """Get all orders for a specific customer"""
    try:
        orders = queue_manager.get_customer_status(customer_name)
        return jsonify({'orders': orders})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """Get queue analytics"""
    try:
        analytics = queue_manager.get_analytics()
        return jsonify(analytics)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/menu', methods=['GET'])
def get_menu():
    """Get coffee shop menu"""
    menu = {
        'beverages': [
            {'id': 1, 'name': 'Espresso', 'price': 2.50, 'prep_time': 3},
            {'id': 2, 'name': 'Americano', 'price': 3.00, 'prep_time': 4},
            {'id': 3, 'name': 'Cappuccino', 'price': 4.00, 'prep_time': 5},
            {'id': 4, 'name': 'Latte', 'price': 4.50, 'prep_time': 5},
            {'id': 5, 'name': 'Mocha', 'price': 5.00, 'prep_time': 6},
            {'id': 6, 'name': 'Frappuccino', 'price': 5.50, 'prep_time': 8},
        ],
        'food': [
            {'id': 7, 'name': 'Croissant', 'price': 3.00, 'prep_time': 2},
            {'id': 8, 'name': 'Sandwich', 'price': 7.00, 'prep_time': 5},
            {'id': 9, 'name': 'Muffin', 'price': 3.50, 'prep_time': 1},
            {'id': 10, 'name': 'Bagel', 'price': 4.00, 'prep_time': 3},
        ]
    }
    return jsonify(menu)

# Initialize cache on startup
update_cache()

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'coffee-shop-queue-system'})

# Cache monitoring endpoint
@app.route('/api/cache/status', methods=['GET'])
def get_cache_status():
    """Get cache status and statistics"""
    return jsonify({
        'version': cache['version'],
        'last_update': cache['last_update'],
        'cache_age_seconds': time.time() - cache['last_update'],
        'queue_length': len(cache['queue_status']['queue_orders']) if cache['queue_status'] else 0,
        'preparing_count': cache['queue_status']['preparing_count'] if cache['queue_status'] else 0
    })

if __name__ == '__main__':
    print("Starting Coffee Shop Queue Management System...")
    port = int(os.environ.get('PORT', 5002))
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    
    print(f"Server running on port {port}")
    print("API endpoints:")
    print("  POST /api/orders - Create new order")
    print("  POST /api/orders/next - Get next order (staff)")
    print("  POST /api/orders/<id>/complete - Complete order")
    print("  DELETE /api/orders/<id>/cancel - Cancel order")
    print("  GET /api/queue/status - Get queue status")
    print("  GET /api/queue/poll - Poll for updates (with version)")
    print("  GET /api/updates - Get all updates (optimized polling)")
    print("  GET /api/analytics - Get analytics")
    print("  GET /api/customer/<name>/orders - Get customer orders")
    print("  GET /api/menu - Get menu")
    print("  GET /api/cache/status - Get cache status")
    print("  GET /api/health - Health check")
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
