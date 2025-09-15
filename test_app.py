import pytest
import json
from app import app, queue_manager
from queue_manager import Priority


@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            # Reset queue manager for each test
            queue_manager.queue.clear()
            queue_manager.priority_queues = {
                Priority.VIP: queue_manager.priority_queues[Priority.VIP].__class__(),
                Priority.MOBILE_ORDER: queue_manager.priority_queues[Priority.MOBILE_ORDER].__class__(),
                Priority.REGULAR: queue_manager.priority_queues[Priority.REGULAR].__class__()
            }
            queue_manager.preparing_orders.clear()
            queue_manager.completed_orders.clear()
            queue_manager.stats = {
                'total_orders': 0,
                'completed_today': 0,
                'average_wait_time': 0,
                'peak_queue_length': 0
            }
            yield client


class TestHealthEndpoint:
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get('/api/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert data['service'] == 'coffee-shop-queue-system'


class TestMenuEndpoint:
    def test_get_menu(self, client):
        """Test menu endpoint returns proper structure"""
        response = client.get('/api/menu')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'beverages' in data
        assert 'food' in data
        assert len(data['beverages']) > 0
        assert len(data['food']) > 0
        
        # Check first beverage structure
        beverage = data['beverages'][0]
        assert 'id' in beverage
        assert 'name' in beverage
        assert 'price' in beverage
        assert 'prep_time' in beverage


class TestOrderEndpoints:
    def test_create_order_success(self, client):
        """Test successful order creation"""
        order_data = {
            'customer_name': 'John Doe',
            'items': ['Latte', 'Croissant'],
            'priority': 'REGULAR'
        }
        
        response = client.post('/api/orders', 
                             json=order_data,
                             content_type='application/json')
        assert response.status_code == 201
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'order' in data
        assert 'message' in data
        assert data['order']['customer_name'] == 'John Doe'
        assert data['order']['items'] == ['Latte', 'Croissant']
        assert data['order']['priority'] == 'REGULAR'
        
    def test_create_order_missing_data(self, client):
        """Test order creation with missing data"""
        order_data = {
            'customer_name': 'John Doe'
            # Missing items
        }
        
        response = client.post('/api/orders',
                             json=order_data,
                             content_type='application/json')
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'error' in data
        
    def test_create_order_invalid_priority(self, client):
        """Test order creation with invalid priority defaults to REGULAR"""
        order_data = {
            'customer_name': 'Jane Smith',
            'items': ['Espresso'],
            'priority': 'INVALID_PRIORITY'
        }
        
        response = client.post('/api/orders',
                             json=order_data,
                             content_type='application/json')
        assert response.status_code == 201
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['order']['priority'] == 'REGULAR'  # Should default to REGULAR
        
    def test_get_next_order_empty_queue(self, client):
        """Test getting next order when queue is empty"""
        response = client.post('/api/orders/next')
        assert response.status_code == 204  # No content
        
    def test_get_next_order_success(self, client):
        """Test successfully getting next order"""
        # First create an order
        order_data = {
            'customer_name': 'John Doe',
            'items': ['Latte'],
            'priority': 'REGULAR'
        }
        client.post('/api/orders', json=order_data, content_type='application/json')
        
        # Then get next order
        response = client.post('/api/orders/next')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'order' in data
        assert data['order']['customer_name'] == 'John Doe'
        
    def test_complete_order_success(self, client):
        """Test completing an order"""
        # Create and start preparing an order
        order_data = {
            'customer_name': 'John Doe',
            'items': ['Latte'],
            'priority': 'REGULAR'
        }
        client.post('/api/orders', json=order_data, content_type='application/json')
        
        next_response = client.post('/api/orders/next')
        next_data = json.loads(next_response.data)
        order_id = next_data['order']['id']
        
        # Complete the order
        response = client.post(f'/api/orders/{order_id}/complete')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['message'] == 'Order completed'
        
    def test_complete_nonexistent_order(self, client):
        """Test completing an order that doesn't exist"""
        response = client.post('/api/orders/nonexistent-id/complete')
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert 'error' in data
        
    def test_cancel_order_success(self, client):
        """Test canceling an order"""
        # Create an order
        order_data = {
            'customer_name': 'John Doe',
            'items': ['Latte'],
            'priority': 'REGULAR'
        }
        create_response = client.post('/api/orders', json=order_data, content_type='application/json')
        create_data = json.loads(create_response.data)
        order_id = create_data['order']['id']
        
        # Cancel the order
        response = client.delete(f'/api/orders/{order_id}/cancel')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['message'] == 'Order cancelled'
        
    def test_cancel_nonexistent_order(self, client):
        """Test canceling an order that doesn't exist"""
        response = client.delete('/api/orders/nonexistent-id/cancel')
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert 'error' in data


class TestQueueStatusEndpoint:
    def test_get_queue_status_empty(self, client):
        """Test queue status when empty"""
        response = client.get('/api/queue/status')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['queue_length'] == 0
        assert data['preparing_count'] == 0
        assert 'estimated_wait_time' in data
        assert data['queue_orders'] == []
        assert data['preparing_orders'] == []
        
    def test_get_queue_status_with_orders(self, client):
        """Test queue status with orders"""
        # Add a couple of orders
        order_data1 = {
            'customer_name': 'John Doe',
            'items': ['Latte'],
            'priority': 'REGULAR'
        }
        order_data2 = {
            'customer_name': 'Jane Smith',
            'items': ['Espresso'],
            'priority': 'VIP'
        }
        
        client.post('/api/orders', json=order_data1, content_type='application/json')
        client.post('/api/orders', json=order_data2, content_type='application/json')
        
        response = client.get('/api/queue/status')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['queue_length'] == 2
        assert len(data['queue_orders']) == 2
        # VIP order should be first
        assert data['queue_orders'][0]['customer_name'] == 'Jane Smith'
        assert data['queue_orders'][1]['customer_name'] == 'John Doe'


class TestCustomerStatusEndpoint:
    def test_get_customer_orders(self, client):
        """Test getting orders for a specific customer"""
        # Add orders for different customers
        order_data1 = {
            'customer_name': 'John Doe',
            'items': ['Latte'],
            'priority': 'REGULAR'
        }
        order_data2 = {
            'customer_name': 'Jane Smith',
            'items': ['Espresso'],
            'priority': 'VIP'
        }
        order_data3 = {
            'customer_name': 'John Doe',  # Second order for John
            'items': ['Cappuccino'],
            'priority': 'REGULAR'
        }
        
        client.post('/api/orders', json=order_data1, content_type='application/json')
        client.post('/api/orders', json=order_data2, content_type='application/json')
        client.post('/api/orders', json=order_data3, content_type='application/json')
        
        response = client.get('/api/customer/John Doe/orders')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'orders' in data
        assert len(data['orders']) == 2
        assert all(order['customer_name'] == 'John Doe' for order in data['orders'])


class TestAnalyticsEndpoint:
    def test_get_analytics(self, client):
        """Test analytics endpoint"""
        # Add and complete some orders
        order_data = {
            'customer_name': 'John Doe',
            'items': ['Latte'],
            'priority': 'REGULAR'
        }
        
        client.post('/api/orders', json=order_data, content_type='application/json')
        next_response = client.post('/api/orders/next')
        next_data = json.loads(next_response.data)
        order_id = next_data['order']['id']
        client.post(f'/api/orders/{order_id}/complete')
        
        response = client.get('/api/analytics')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'stats' in data
        assert 'queue_by_priority' in data
        assert 'recent_completions' in data
        assert data['stats']['total_orders'] == 1
        assert data['stats']['completed_today'] == 1


class TestOrderWorkflow:
    def test_complete_order_workflow(self, client):
        """Test a complete order workflow"""
        # 1. Create order
        order_data = {
            'customer_name': 'Integration Test',
            'items': ['Latte', 'Croissant'],
            'priority': 'VIP'
        }
        
        create_response = client.post('/api/orders', json=order_data, content_type='application/json')
        assert create_response.status_code == 201
        create_data = json.loads(create_response.data)
        order_id = create_data['order']['id']
        
        # 2. Check queue status
        status_response = client.get('/api/queue/status')
        status_data = json.loads(status_response.data)
        assert status_data['queue_length'] == 1
        assert status_data['queue_orders'][0]['id'] == order_id
        
        # 3. Get next order for preparation
        next_response = client.post('/api/orders/next')
        assert next_response.status_code == 200
        next_data = json.loads(next_response.data)
        assert next_data['order']['id'] == order_id
        
        # 4. Check queue status again (should be empty, preparing should have 1)
        status_response = client.get('/api/queue/status')
        status_data = json.loads(status_response.data)
        assert status_data['queue_length'] == 0
        assert status_data['preparing_count'] == 1
        
        # 5. Complete order
        complete_response = client.post(f'/api/orders/{order_id}/complete')
        assert complete_response.status_code == 200
        
        # 6. Check final status
        status_response = client.get('/api/queue/status')
        status_data = json.loads(status_response.data)
        assert status_data['queue_length'] == 0
        assert status_data['preparing_count'] == 0
        
        # 7. Check analytics
        analytics_response = client.get('/api/analytics')
        analytics_data = json.loads(analytics_response.data)
        assert analytics_data['stats']['completed_today'] == 1
