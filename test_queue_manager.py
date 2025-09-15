import pytest
from queue_manager import QueueManager, Order, Priority, OrderStatus
from datetime import datetime


class TestOrder:
    def test_order_creation(self):
        """Test basic order creation"""
        order = Order("John Doe", ["Latte", "Croissant"], Priority.REGULAR)
        
        assert order.customer_name == "John Doe"
        assert order.items == ["Latte", "Croissant"]
        assert order.priority == Priority.REGULAR
        assert order.status == OrderStatus.QUEUED
        assert order.id is not None
        assert order.created_at is not None
        assert order.estimated_wait_time == 9  # 5 base + 2*2 items
        
    def test_order_to_dict(self):
        """Test order serialization"""
        order = Order("Jane Smith", ["Espresso"], Priority.VIP)
        order_dict = order.to_dict()
        
        assert order_dict["customer_name"] == "Jane Smith"
        assert order_dict["items"] == ["Espresso"]
        assert order_dict["priority"] == "VIP"
        assert order_dict["status"] == "queued"
        assert "id" in order_dict
        assert "created_at" in order_dict


class TestQueueManager:
    def test_queue_manager_initialization(self):
        """Test queue manager initializes correctly"""
        qm = QueueManager()
        
        assert len(qm.queue) == 0
        assert len(qm.priority_queues) == 3
        assert len(qm.preparing_orders) == 0
        assert len(qm.completed_orders) == 0
        assert qm.stats["total_orders"] == 0
        
    def test_add_regular_order(self):
        """Test adding a regular order"""
        qm = QueueManager()
        order = qm.add_order("John", ["Latte"], Priority.REGULAR)
        
        assert len(qm.queue) == 1
        assert qm.stats["total_orders"] == 1
        assert order.position_in_queue == 1
        assert qm.queue[0] == order
        
    def test_add_vip_order_priority(self):
        """Test VIP orders get priority"""
        qm = QueueManager()
        
        # Add regular order first
        regular_order = qm.add_order("John", ["Latte"], Priority.REGULAR)
        
        # Add VIP order - should jump to front
        vip_order = qm.add_order("Jane", ["Espresso"], Priority.VIP)
        
        assert len(qm.queue) == 2
        assert qm.queue[0] == vip_order  # VIP should be first
        assert qm.queue[1] == regular_order
        assert vip_order.position_in_queue == 1
        assert regular_order.position_in_queue == 2
        
    def test_get_next_order(self):
        """Test getting next order from queue"""
        qm = QueueManager()
        
        # Add two orders
        order1 = qm.add_order("John", ["Latte"], Priority.REGULAR)
        order2 = qm.add_order("Jane", ["Espresso"], Priority.REGULAR)
        
        # Get next order
        next_order = qm.get_next_order()
        
        assert next_order == order1
        assert next_order.status == OrderStatus.PREPARING
        assert len(qm.queue) == 1  # Should have one less in queue
        assert len(qm.preparing_orders) == 1
        assert order1.id in qm.preparing_orders
        
    def test_get_next_order_empty_queue(self):
        """Test getting next order when queue is empty"""
        qm = QueueManager()
        next_order = qm.get_next_order()
        
        assert next_order is None
        
    def test_complete_order(self):
        """Test completing an order"""
        qm = QueueManager()
        
        # Add and start preparing an order
        order = qm.add_order("John", ["Latte"], Priority.REGULAR)
        preparing_order = qm.get_next_order()
        
        # Complete the order
        success = qm.complete_order(preparing_order.id)
        
        assert success is True
        assert preparing_order.id not in qm.preparing_orders
        assert len(qm.completed_orders) == 1
        assert qm.stats["completed_today"] == 1
        assert preparing_order.status == OrderStatus.COMPLETED
        
    def test_complete_nonexistent_order(self):
        """Test completing an order that doesn't exist"""
        qm = QueueManager()
        success = qm.complete_order("nonexistent-id")
        
        assert success is False
        
    def test_cancel_order_in_queue(self):
        """Test canceling an order that's still in queue"""
        qm = QueueManager()
        
        # Add two orders
        order1 = qm.add_order("John", ["Latte"], Priority.REGULAR)
        order2 = qm.add_order("Jane", ["Espresso"], Priority.REGULAR)
        
        # Cancel the first order
        success = qm.cancel_order(order1.id)
        
        assert success is True
        assert len(qm.queue) == 1
        assert qm.queue[0] == order2
        assert order1.status == OrderStatus.CANCELLED
        assert order2.position_in_queue == 1  # Position should update
        
    def test_cancel_preparing_order(self):
        """Test canceling an order that's being prepared"""
        qm = QueueManager()
        
        # Add and start preparing an order
        order = qm.add_order("John", ["Latte"], Priority.REGULAR)
        preparing_order = qm.get_next_order()
        
        # Cancel the preparing order
        success = qm.cancel_order(preparing_order.id)
        
        assert success is True
        assert len(qm.preparing_orders) == 0
        assert preparing_order.status == OrderStatus.CANCELLED
        
    def test_get_queue_status(self):
        """Test getting queue status"""
        qm = QueueManager()
        
        # Add some orders
        qm.add_order("John", ["Latte"], Priority.REGULAR)
        qm.add_order("Jane", ["Espresso"], Priority.VIP)
        
        # Start preparing one order
        qm.get_next_order()
        
        status = qm.get_queue_status()
        
        assert status["queue_length"] == 1
        assert status["preparing_count"] == 1
        assert "estimated_wait_time" in status
        assert len(status["queue_orders"]) == 1
        assert len(status["preparing_orders"]) == 1
        
    def test_get_customer_status(self):
        """Test getting status for a specific customer"""
        qm = QueueManager()
        
        # Add orders for different customers
        qm.add_order("John", ["Latte"], Priority.REGULAR)
        qm.add_order("Jane", ["Espresso"], Priority.REGULAR)
        qm.add_order("John", ["Cappuccino"], Priority.VIP)  # Second order for John
        
        customer_orders = qm.get_customer_status("John")
        
        assert len(customer_orders) == 2
        assert all(order["customer_name"] == "John" for order in customer_orders)
        
    def test_priority_queue_ordering(self):
        """Test that priority queues maintain correct order"""
        qm = QueueManager()
        
        # Add orders in mixed priority order
        regular1 = qm.add_order("Regular1", ["Latte"], Priority.REGULAR)
        mobile1 = qm.add_order("Mobile1", ["Espresso"], Priority.MOBILE_ORDER)
        vip1 = qm.add_order("VIP1", ["Cappuccino"], Priority.VIP)
        regular2 = qm.add_order("Regular2", ["Americano"], Priority.REGULAR)
        vip2 = qm.add_order("VIP2", ["Mocha"], Priority.VIP)
        
        # Check order in main queue: VIP first, then Mobile, then Regular
        expected_order = [vip1, vip2, mobile1, regular1, regular2]
        actual_order = list(qm.queue)
        
        assert actual_order == expected_order
        
    def test_get_analytics(self):
        """Test getting analytics data"""
        qm = QueueManager()
        
        # Add and complete some orders
        order1 = qm.add_order("John", ["Latte"], Priority.REGULAR)
        order2 = qm.add_order("Jane", ["Espresso"], Priority.VIP)
        
        preparing_order = qm.get_next_order()
        qm.complete_order(preparing_order.id)
        
        analytics = qm.get_analytics()
        
        assert "stats" in analytics
        assert analytics["stats"]["total_orders"] == 2
        assert analytics["stats"]["completed_today"] == 1
        assert "queue_by_priority" in analytics
        assert "recent_completions" in analytics
        
    def test_estimated_wait_time_calculation(self):
        """Test estimated wait time calculation"""
        qm = QueueManager()
        
        # Empty queue should have base time
        status = qm.get_queue_status()
        assert status["estimated_wait_time"] == 5
        
        # Add orders and check calculation
        qm.add_order("John", ["Latte"], Priority.REGULAR)  # 7 minutes
        qm.add_order("Jane", ["Espresso", "Croissant"], Priority.REGULAR)  # 9 minutes
        
        status = qm.get_queue_status()
        # Should be average of order wait times, minimum 5
        assert status["estimated_wait_time"] >= 5


# Integration-style tests for the queue operations
class TestQueueIntegration:
    def test_full_order_lifecycle(self):
        """Test complete order lifecycle"""
        qm = QueueManager()
        
        # Create order
        order = qm.add_order("John Doe", ["Latte", "Croissant"], Priority.REGULAR)
        assert order.status == OrderStatus.QUEUED
        assert len(qm.queue) == 1
        
        # Start preparing
        preparing_order = qm.get_next_order()
        assert preparing_order.status == OrderStatus.PREPARING
        assert len(qm.queue) == 0
        assert len(qm.preparing_orders) == 1
        
        # Complete order
        success = qm.complete_order(preparing_order.id)
        assert success is True
        assert preparing_order.status == OrderStatus.COMPLETED
        assert len(qm.preparing_orders) == 0
        assert len(qm.completed_orders) == 1
        assert qm.stats["completed_today"] == 1
        
    def test_mixed_priority_workflow(self):
        """Test workflow with mixed priority orders"""
        qm = QueueManager()
        
        # Add orders in different priorities
        regular = qm.add_order("Regular Customer", ["Americano"], Priority.REGULAR)
        vip = qm.add_order("VIP Customer", ["Espresso"], Priority.VIP)
        mobile = qm.add_order("Mobile Customer", ["Latte"], Priority.MOBILE_ORDER)
        
        # VIP should be processed first
        next_order = qm.get_next_order()
        assert next_order.customer_name == "VIP Customer"
        
        # Mobile should be next
        next_order = qm.get_next_order()
        assert next_order.customer_name == "Mobile Customer"
        
        # Regular should be last
        next_order = qm.get_next_order()
        assert next_order.customer_name == "Regular Customer"
