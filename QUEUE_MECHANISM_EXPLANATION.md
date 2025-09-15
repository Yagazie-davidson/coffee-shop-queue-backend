# Coffee Shop Queue System - Technical Deep Dive

## Overview

This is a **priority-based queue management system** for a coffee shop that handles real-time order processing with multiple priority levels and status tracking.

## Core Architecture

### 1. **Data Structures Used**

#### **Primary Data Structures:**

- **`deque()` (Double-ended queue)** - Main queue for FIFO operations
- **`dict`** - Priority queues and order tracking
- **`list`** - Completed orders history

#### **Why deque()?**

- **O(1) operations** for adding/removing from both ends
- **Efficient** for queue operations (FIFO)
- **Memory efficient** compared to list for frequent insertions/deletions

### 2. **Order Lifecycle & States**

```
QUEUED → PREPARING → COMPLETED
   ↓         ↓
CANCELLED  CANCELLED
```

**Order States:**

- **QUEUED**: Order placed, waiting in queue
- **PREPARING**: Order being made by staff
- **COMPLETED**: Order finished and picked up
- **CANCELLED**: Order cancelled (can happen at any stage)

### 3. **Priority System**

**Three Priority Levels:**

1. **VIP** (Priority 2) - Highest priority
2. **MOBILE_ORDER** (Priority 3) - Pre-orders
3. **REGULAR** (Priority 1) - Walk-in customers

**Priority Logic:**

- VIP orders always go first
- Mobile orders come before regular orders
- Within same priority: **FIFO** (First In, First Out)

## Queue Management Algorithm

### **Dual Queue Architecture**

The system uses **two queue structures**:

1. **Priority Queues** (3 separate deques):

   ```python
   priority_queues = {
       Priority.VIP: deque(),
       Priority.MOBILE_ORDER: deque(),
       Priority.REGULAR: deque()
   }
   ```

2. **Main Queue** (single deque):
   ```python
   queue = deque()  # Rebuilt from priority queues
   ```

### **Why This Design?**

**Benefits:**

- **Easy priority management** - Add to correct priority queue
- **Efficient ordering** - Rebuild main queue when needed
- **Flexible** - Can easily add new priority levels
- **Clear separation** - Each priority handled independently

**Trade-offs:**

- **Memory overhead** - Storing orders in multiple places
- **Rebuild cost** - Main queue rebuilt on every change
- **Complexity** - More complex than single queue

## Key Operations Breakdown

### **1. Adding Orders (`add_order`)**

```python
def add_order(self, customer_name, items, priority):
    # 1. Create order object
    order = Order(customer_name, items, priority)

    # 2. Add to appropriate priority queue
    self.priority_queues[priority].append(order)

    # 3. Rebuild main queue (VIP → Mobile → Regular)
    self._rebuild_main_queue()

    # 4. Update statistics
    self.stats['total_orders'] += 1
```

**Time Complexity:** O(n) where n = total orders (due to rebuild)

### **2. Getting Next Order (`get_next_order`)**

```python
def get_next_order(self):
    # 1. Get first order from main queue (highest priority)
    order = self.queue.popleft()

    # 2. Remove from priority queue
    for priority_queue in self.priority_queues.values():
        priority_queue.remove(order)  # O(n) operation

    # 3. Change status to PREPARING
    order.status = OrderStatus.PREPARING
    self.preparing_orders[order.id] = order

    # 4. Rebuild main queue for remaining orders
    self._rebuild_main_queue()
```

**Time Complexity:** O(n) due to remove() and rebuild

### **3. Queue Rebuilding (`_rebuild_main_queue`)**

```python
def _rebuild_main_queue(self):
    self.queue.clear()

    # Add in priority order: VIP → Mobile → Regular
    for priority in [Priority.VIP, Priority.MOBILE_ORDER, Priority.REGULAR]:
        self.queue.extend(self.priority_queues[priority])

    # Update position numbers
    for position, order in enumerate(self.queue):
        order.position_in_queue = position + 1
```

**This ensures:**

- Correct priority ordering
- Accurate position tracking
- Consistent state across all queues

## Wait Time Calculation

### **Individual Order Wait Time**

```python
def _calculate_wait_time(self):
    base_time = 5  # 5 minutes base
    item_time = len(self.items) * 2  # 2 minutes per item
    return base_time + item_time
```

### **Queue Wait Time Estimation**

```python
def _calculate_estimated_wait_time(self):
    if not self.queue:
        return 5  # Base time if empty

    # Average of first 5 orders
    total_wait = sum(order.estimated_wait_time for order in list(self.queue)[:5])
    return max(5, total_wait // min(5, len(self.queue)))
```

## Real-Time Updates

### **SocketIO Integration**

- **Queue updates** broadcast to all customers
- **Analytics updates** sent to staff dashboard
- **Room-based messaging** (queue_room, staff_room)

### **Event Flow**

1. Order created → `queue_updated` event
2. Order started → `order_started` event
3. Order completed → `order_completed` event
4. Order cancelled → `order_cancelled` event

## Performance Characteristics

### **Time Complexities**

- **Add Order**: O(n) - due to queue rebuild
- **Get Next Order**: O(n) - due to remove + rebuild
- **Complete Order**: O(1) - hash table lookup
- **Cancel Order**: O(n) - linear search + rebuild

### **Space Complexity**

- **O(n)** where n = number of orders
- Orders stored in multiple data structures
- Completed orders kept in memory (could be optimized)

## Scalability Considerations

### **Current Limitations**

1. **O(n) operations** - Won't scale to thousands of orders
2. **In-memory storage** - Data lost on restart
3. **No persistence** - No historical data
4. **Single-threaded** - No concurrent processing

### **Potential Optimizations**

1. **Database persistence** - SQLite/PostgreSQL
2. **Indexed data structures** - For O(log n) operations
3. **Caching layer** - Redis for real-time data
4. **Microservices** - Separate queue service
5. **Message queues** - RabbitMQ/Apache Kafka

## Interview Talking Points

### **Strengths to Highlight**

1. **Clean separation of concerns** - Order, QueueManager, API layers
2. **Priority-based processing** - Handles different customer types
3. **Real-time updates** - SocketIO for live experience
4. **Comprehensive tracking** - Full order lifecycle
5. **Statistics and analytics** - Business insights

### **Technical Decisions Explained**

1. **Why deque()?** - Efficient FIFO operations
2. **Why dual queues?** - Easy priority management
3. **Why rebuild?** - Ensures consistency
4. **Why in-memory?** - Simplicity for MVP

### **Improvement Areas**

1. **Database integration** - For persistence
2. **Performance optimization** - Reduce O(n) operations
3. **Error handling** - More robust error management
4. **Testing** - More comprehensive test coverage
5. **Monitoring** - Better observability

## Code Quality Features

### **Good Practices Used**

- **Type hints** - Better code documentation
- **Enum classes** - Type safety for status/priority
- **Method documentation** - Clear docstrings
- **Error handling** - Try/catch blocks
- **Separation of concerns** - Clean architecture

### **Design Patterns**

- **State Pattern** - Order status management
- **Strategy Pattern** - Priority handling
- **Observer Pattern** - Real-time updates via SocketIO

This system demonstrates understanding of:

- **Data structures** and their trade-offs
- **Real-time systems** with WebSockets
- **Priority queuing** algorithms
- **System design** considerations
- **Performance analysis** and optimization
