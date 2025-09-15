from collections import deque
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional
import uuid

class OrderStatus(Enum):
    QUEUED = "queued"
    PREPARING = "preparing"
    READY = "ready"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Priority(Enum):
    REGULAR = 1
    VIP = 2
    MOBILE_ORDER = 3

class Order:
    def __init__(self, customer_name: str, items: List[str], priority: Priority = Priority.REGULAR):
        self.id = str(uuid.uuid4())
        self.customer_name = customer_name
        self.items = items
        self.priority = priority
        self.status = OrderStatus.QUEUED
        self.created_at = datetime.now()
        self.estimated_wait_time = self._calculate_wait_time()
        self.position_in_queue = None
    
    def _calculate_wait_time(self) -> int:
        """Calculate estimated wait time based on number of items"""
        base_time = 5  # 5 minutes base time
        item_time = len(self.items) * 2  # 2 minutes per item
        return base_time + item_time
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'customer_name': self.customer_name,
            'items': self.items,
            'priority': self.priority.name,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'estimated_wait_time': self.estimated_wait_time,
            'position_in_queue': self.position_in_queue
        }

class QueueManager:
    def __init__(self):
        self.queue = deque()
        self.priority_queues = {
            Priority.VIP: deque(),
            Priority.MOBILE_ORDER: deque(),
            Priority.REGULAR: deque()
        }
        # Orders being prepared
        self.preparing_orders = {}
        # Completed orders history
        self.completed_orders = []
        # Queue statistics
        self.stats = {
            'total_orders': 0,
            'completed_today': 0,
            'average_wait_time': 0,
            'peak_queue_length': 0
        }
    
    def add_order(self, customer_name: str, items: List[str], priority: Priority = Priority.REGULAR) -> Order:
        """Add a new order to the appropriate queue"""
        order = Order(customer_name, items, priority)
        
        # Add to priority-specific queue
        self.priority_queues[priority].append(order)
        
        # Update main queue with proper ordering
        self._rebuild_main_queue()
        
        # Update statistics
        self.stats['total_orders'] += 1
        current_queue_length = len(self.queue)
        if current_queue_length > self.stats['peak_queue_length']:
            self.stats['peak_queue_length'] = current_queue_length
        
        return order
    
    def _rebuild_main_queue(self):
        """Rebuild main queue respecting priority order"""
        self.queue.clear()
        
        # Add orders in priority order: VIP -> Mobile -> Regular
        for priority in [Priority.VIP, Priority.MOBILE_ORDER, Priority.REGULAR]:
            self.queue.extend(self.priority_queues[priority])
        
        for position, order in enumerate(self.queue):
            order.position_in_queue = position + 1
    
    def get_next_order(self) -> Optional[Order]:
        """Get the next order from the queue (FIFO with priority)"""
        if not self.queue:
            return None
        
        order = self.queue.popleft()
        
        for priority_queue in self.priority_queues.values():
            try:
                priority_queue.remove(order)
                break
            except ValueError:
                continue
        
        # Move to preparing
        order.status = OrderStatus.PREPARING
        self.preparing_orders[order.id] = order
        
        # Update positions for remaining orders
        self._rebuild_main_queue()
        
        return order
    
    def complete_order(self, order_id: str) -> bool:
        """Mark an order as completed"""
        if order_id not in self.preparing_orders:
            return False
        
        order = self.preparing_orders.pop(order_id)
        order.status = OrderStatus.COMPLETED
        self.completed_orders.append(order)
        
        # Update statistics
        self.stats['completed_today'] += 1
        actual_wait_time = (datetime.now() - order.created_at).total_seconds() / 60
        self._update_average_wait_time(actual_wait_time)
        
        return True
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order (remove from queue or preparing)"""
        # Check if in queue
        for order in list(self.queue):
            if order.id == order_id:
                order.status = OrderStatus.CANCELLED
                self.queue.remove(order)
                # Remove from priority queue as well
                for priority_queue in self.priority_queues.values():
                    try:
                        priority_queue.remove(order)
                        break
                    except ValueError:
                        continue
                self._rebuild_main_queue()
                return True
        
        # Check if preparing
        if order_id in self.preparing_orders:
            order = self.preparing_orders.pop(order_id)
            order.status = OrderStatus.CANCELLED
            return True
        
        return False
    
    def get_queue_status(self) -> Dict:
        """Get current queue status"""
        return {
            'queue_length': len(self.queue),
            'preparing_count': len(self.preparing_orders),
            'estimated_wait_time': self._calculate_estimated_wait_time(),
            'queue_orders': [order.to_dict() for order in list(self.queue)[:10]],  # Show first 10
            'preparing_orders': [order.to_dict() for order in self.preparing_orders.values()]
        }
    
    def get_customer_status(self, customer_name: str) -> List[Dict]:
        """Get status of all orders for a specific customer"""
        customer_orders = []
        
        # Check queue
        for order in self.queue:
            if order.customer_name.lower() == customer_name.lower():
                customer_orders.append(order.to_dict())
        
        # Check preparing
        for order in self.preparing_orders.values():
            if order.customer_name.lower() == customer_name.lower():
                customer_orders.append(order.to_dict())
        
        return customer_orders
    
    def _calculate_estimated_wait_time(self) -> int:
        """Calculate estimated wait time for new customers"""
        if not self.queue:
            return 5  # Base time if queue is empty
        
        total_wait = sum(order.estimated_wait_time for order in list(self.queue)[:5])  # Average of first 5
        return max(5, total_wait // min(5, len(self.queue)))
    
    def _update_average_wait_time(self, actual_wait_time: float):
        """Update rolling average wait time"""
        if self.stats['completed_today'] == 1:
            self.stats['average_wait_time'] = actual_wait_time
        else:
            # Simple moving average
            current_avg = self.stats['average_wait_time']
            new_avg = (current_avg * (self.stats['completed_today'] - 1) + actual_wait_time) / self.stats['completed_today']
            self.stats['average_wait_time'] = round(new_avg, 1)
    
    def get_analytics(self) -> Dict:
        """Get queue analytics and statistics"""
        return {
            'stats': self.stats,
            'queue_by_priority': {
                priority.name: len(queue) for priority, queue in self.priority_queues.items()
            },
            'recent_completions': [order.to_dict() for order in self.completed_orders[-10:]]
        }
