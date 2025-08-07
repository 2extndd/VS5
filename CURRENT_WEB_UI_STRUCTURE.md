# Текущая структура Web UI - Vinted Notifications Bot

## 📁 **Файловая структура**

```
web_ui_plugin/
├── web_ui.py                 # Основной Flask сервер с роутами
├── static/
│   ├── css/
│   │   └── custom.css        # Кастомные CSS стили
│   ├── favicon.ico           # Иконка сайта (fallback)
│   └── favicon.svg           # Иконка сайта (основная)
└── templates/
    ├── base.html             # Базовый шаблон со всей структурой
    ├── index.html            # Главная страница (Dashboard)
    ├── queries.html          # Управление запросами
    ├── items.html            # Просмотр товаров
    ├── config.html           # Настройки системы
    └── logs.html             # Системные логи
```

## 🌐 **Роуты и функционал (web_ui.py)**

### **Основные страницы**
```python
@app.route('/')                    # Dashboard - главная страница
@app.route('/queries')             # Управление поисковыми запросами
@app.route('/items')               # Просмотр найденных товаров
@app.route('/config')              # Настройки системы
@app.route('/logs')                # Системные логи
```

### **API endpoints для управления**
```python
# Управление запросами
@app.route('/add_query', methods=['POST'])           # Добавить новый запрос
@app.route('/remove_query/<int:query_id>', methods=['POST'])  # Удалить запрос
@app.route('/edit_query/<int:query_id>', methods=['POST'])    # Редактировать запрос
@app.route('/update_thread_id/<int:query_id>', methods=['POST']) # Обновить Thread ID

# Управление товарами  
@app.route('/clear_items', methods=['POST'])         # Очистить все товары

# Управление allowlist
@app.route('/add_country', methods=['POST'])         # Добавить страну в allowlist
@app.route('/remove_country', methods=['POST'])      # Удалить страну из allowlist
@app.route('/clear_allowlist', methods=['POST'])     # Очистить весь allowlist

# Конфигурация
@app.route('/update_config', methods=['POST'])       # Сохранить настройки
@app.route('/start_process/<process_name>', methods=['POST'])  # Запустить процесс
@app.route('/stop_process/<process_name>', methods=['POST'])   # Остановить процесс

# Railway управление
@app.route('/force_redeploy', methods=['POST'])      # Принудительный редеплой
@app.route('/redeploy_status')                       # Статус системы редеплоя
@app.route('/proxy_status')                          # Статус прокси системы

# Принудительное сканирование
@app.route('/force_scan', methods=['POST'])          # Force Scan All
```

## 🎨 **Базовый шаблон (base.html)**

### **HTML структура**
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <!-- Bootstrap 5.3.0 CSS -->
    <!-- Bootstrap Icons -->
    <!-- Custom CSS -->
    <!-- Favicon (SVG + ICO) -->
</head>
<body>
    <!-- Навигационное меню -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container-fluid">
            <a class="navbar-brand">Vinted Notifications</a>
            <button class="navbar-toggler"><!-- Mobile menu toggle --></button>
            
            <div class="navbar-nav">
                <a href="/">Dashboard</a>
                <a href="/queries">Queries</a>
                <a href="/items">Items</a>
                <a href="/config">Configuration</a>
                <a href="/logs">Logs</a>
            </div>
        </div>
    </nav>

    <!-- Flash сообщения -->
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="alert alert-{{ 'danger' if category == 'error' else category }}">
                    {{ message }}
                </div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    <!-- Основной контент -->
    <main class="container-fluid py-4">
        {% block content %}{% endblock %}
    </main>

    <!-- Футер -->
    <footer class="bg-light py-4 mt-auto">
        <div class="container">
            <div class="row">
                <div class="col-md-4">
                    <a href="https://t.me/extndd">@extndd</a>
                    <a href="https://t.me/extnddlifeceo">@extnddlifeceo</a>
                </div>
                <div class="col-md-4 text-end">
                    <strong>Vinted Notificator</strong>
                    <a href="https://github.com/2extndd/VS5">github.com/2extndd/VS5</a>
                </div>
            </div>
        </div>
    </footer>

    <!-- Bootstrap JS -->
    <!-- Auto-dismiss flash messages -->
</body>
</html>
```

### **Мобильная адаптация в CSS**
```css
@media (max-width: 768px) {
    .table-responsive { font-size: 0.85rem; }
    .btn-group .btn { font-size: 0.75rem; padding: 0.25rem 0.5rem; }
    .card-body { padding: 1rem 0.75rem; }
    .container-fluid { padding-left: 0.5rem; padding-right: 0.5rem; }
    .navbar-nav .nav-link { padding: 0.5rem 0.75rem; text-align: center; }
}
```

## 📊 **Dashboard (index.html)**

### **Статистические карточки**
```html
<div class="row mb-4">
    <!-- Total Items -->
    <div class="col-md-3 mb-3">
        <div class="card bg-primary text-white">
            <div class="card-body text-center">
                <h2 class="card-title">{{ stats.total_items }}</h2>
                <p class="card-text">Items grabbed for monitored queries so far</p>
            </div>
        </div>
    </div>
    
    <!-- Active Queries -->
    <div class="col-md-3 mb-3">
        <div class="card bg-success text-white">
            <div class="card-body text-center">
                <h2 class="card-title">{{ stats.total_queries }}</h2>
                <p class="card-text">Queries being monitored</p>
            </div>
        </div>
    </div>
    
    <!-- API Requests -->
    <div class="col-md-3 mb-3">
        <div class="card bg-info text-white">
            <div class="card-body text-center">
                <h2 class="card-title">{{ stats.api_requests }}</h2>
                <p class="card-text">Requests to Vinted since start</p>
            </div>
        </div>
    </div>
    
    <!-- Uptime -->
    <div class="col-md-3 mb-3">
        <div class="card bg-warning text-dark">
            <div class="card-body text-center">
                <h2 class="card-title">{{ stats.bot_uptime }}</h2>
                <p class="card-text">Uptime</p>
            </div>
        </div>
    </div>
</div>
```

### **Last Found Item**
```html
<div class="row mb-4">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header">
                <h5><i class="bi bi-clock-history me-2"></i>Last Found Item</h5>
            </div>
            <div class="card-body">
                {% if last_item %}
                    <div class="d-flex align-items-center">
                        <img src="{{ last_item.photo_url }}" class="me-3" 
                             style="width: 80px; height: 80px; object-fit: cover;">
                        <div>
                            <h6>{{ last_item.title }}</h6>
                            <small class="text-muted">{{ last_item.timestamp }}</small>
                            <div><a href="{{ last_item.url }}" class="btn btn-sm btn-primary">View</a></div>
                        </div>
                    </div>
                {% else %}
                    <p class="text-muted">No items found yet</p>
                {% endif %}
            </div>
        </div>
    </div>
</div>
```

### **Recent Items с управлением**
```html
<div class="row">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
                <div class="d-flex align-items-center">
                    <i class="bi bi-box me-2 text-info"></i>
                    <h5 class="card-title mb-0">Recent Items</h5>
                </div>
                <div class="d-flex align-items-center">
                    <!-- Force Scan All -->
                    <button class="btn btn-primary btn-sm me-2" id="forceScanBtn">
                        <i class="bi bi-arrow-clockwise me-1"></i>Force Scan All
                    </button>
                    
                    <!-- View Toggle -->
                    <div class="btn-group me-2" role="group">
                        <button type="button" class="btn btn-sm btn-outline-secondary" id="cardViewBtn">
                            <i class="bi bi-grid-3x3-gap-fill"></i> Cards
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-secondary" id="listViewBtn">
                            <i class="bi bi-list-ul"></i> List
                        </button>
                    </div>
                    
                    <!-- Actions -->
                    <a href="/items" class="btn btn-sm btn-outline-primary me-2">View All</a>
                    <button class="btn btn-sm btn-outline-danger" data-bs-toggle="modal" data-bs-target="#clearItemsModal">
                        <i class="bi bi-trash"></i> Clear All Items
                    </button>
                </div>
            </div>
            
            <div class="card-body">
                <!-- Cards View -->
                <div class="row" id="cardView">
                    {% for item in items %}
                    <div class="col-md-4 col-lg-3 mb-3">
                        <div class="card h-100">
                            <!-- Кликабельное фото -->
                            <a href="{{ item.url }}" target="_blank" class="text-decoration-none">
                                <img src="{{ item.photo_url }}" class="card-img-top" 
                                     style="aspect-ratio: 4/5; object-fit: cover;">
                            </a>
                            
                            <div class="card-body p-2">
                                <h6 class="card-title">{{ item.title }}</h6>
                                <p class="card-text small">
                                    Price: {{ item.price }} {{ item.currency }}<br>
                                    {% if item.brand_title %}<small class="text-muted">{{ item.brand_title }}</small><br>{% endif %}
                                    Date: {{ item.timestamp }}
                                </p>
                            </div>
                            
                            <div class="card-footer bg-white p-2">
                                <a href="{{ item.url }}" target="_blank" class="btn btn-sm btn-primary w-100">
                                    View
                                </a>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>

                <!-- List View (таблица) -->
                <div class="table-responsive" id="listView" style="display: none;">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>Image</th>
                                <th>Title</th>
                                <th>Price</th>
                                <th>Timestamp</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for item in items %}
                            <tr>
                                <td><img src="{{ item.photo_url }}" style="width: 50px; height: 50px;"></td>
                                <td>{{ item.title }}</td>
                                <td>
                                    {{ item.price }} {{ item.currency }}
                                    {% if item.brand_title %}<br><small>{{ item.brand_title }}</small>{% endif %}
                                </td>
                                <td>{{ item.timestamp }}</td>
                                <td><a href="{{ item.url }}" class="btn btn-sm btn-outline-primary">View</a></td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>
```

### **JavaScript функционал**
```javascript
<script>
// Auto-refresh каждые 10 секунд
setInterval(function() {
    if (document.visibilityState === 'visible') {
        location.reload();
    }
}, 10000);

// Cards/List view toggle
document.getElementById('cardViewBtn').addEventListener('click', function() {
    document.getElementById('cardView').style.display = 'flex';
    document.getElementById('listView').style.display = 'none';
    this.classList.add('active');
    document.getElementById('listViewBtn').classList.remove('active');
    localStorage.setItem('vintedViewPreference', 'card');
});

// Force Scan All
document.getElementById('forceScanBtn').addEventListener('click', function() {
    fetch('/force_scan', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            // Show toast notification
        });
});
</script>
```

## 📝 **Queries (queries.html)**

### **Добавление нового запроса**
```html
<div class="row mb-4">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header">
                <h5><i class="bi bi-plus-circle me-2"></i>Add New Query</h5>
            </div>
            <div class="card-body">
                <form action="/add_query" method="post">
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group mb-3">
                                <label for="query" class="form-label">Vinted Search URL</label>
                                <input type="url" class="form-control" id="query" name="query" required>
                                <small class="form-text text-muted">Paste the full Vinted search URL</small>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="form-group mb-3">
                                <label for="name" class="form-label">Query Name (Optional)</label>
                                <input type="text" class="form-control" id="name" name="name">
                            </div>
                        </div>
                        <div class="col-md-2">
                            <div class="form-group mb-3">
                                <label for="thread_id" class="form-label">Thread ID</label>
                                <input type="number" class="form-control" id="thread_id" name="thread_id">
                            </div>
                        </div>
                        <div class="col-md-1 d-flex align-items-end">
                            <button type="submit" class="btn btn-primary w-100">
                                <i class="bi bi-plus"></i> Add
                            </button>
                        </div>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
```

### **Таблица запросов**
```html
<div class="row">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header">
                <h5><i class="bi bi-list-ul me-2"></i>Active Queries ({{ queries|length }})</h5>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Query Name</th>
                                <th>Items Found</th>
                                <th>Last Found Item</th>
                                <th>Thread ID</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for query in queries %}
                            <tr>
                                <td><span class="badge bg-primary">{{ loop.index }}</span></td>
                                <td>
                                    <a href="{{ query.query }}" target="_blank" class="text-decoration-none">
                                        {{ query.display_name }}
                                    </a>
                                </td>
                                <td>
                                    <a href="/items?query={{ query.query_id }}" class="btn btn-sm btn-outline-info">
                                        {{ query.items_count }} items
                                    </a>
                                </td>
                                <td>
                                    {% if query.last_item_date %}
                                        <span class="badge bg-success">{{ query.last_item_date }}</span>
                                    {% else %}
                                        <span class="badge bg-secondary">Never</span>
                                    {% endif %}
                                </td>
                                <td>
                                    <form action="/update_thread_id/{{ query.query_id }}" method="post" class="d-inline">
                                        <div class="input-group input-group-sm">
                                            <input type="number" class="form-control" name="thread_id" 
                                                   value="{{ query.thread_id or '' }}" style="width: 80px;">
                                            <button class="btn btn-outline-secondary" type="submit">
                                                <i class="bi bi-check"></i>
                                            </button>
                                        </div>
                                    </form>
                                </td>
                                <td>
                                    <div class="btn-group" role="group">
                                        <a href="/items?query={{ query.query_id }}" class="btn btn-sm btn-outline-primary">
                                            <i class="bi bi-eye"></i> View Items
                                        </a>
                                        <button class="btn btn-sm btn-outline-warning" data-bs-toggle="modal" 
                                                data-bs-target="#editModal{{ query.query_id }}">
                                            <i class="bi bi-pencil"></i> Edit
                                        </button>
                                        <form action="/remove_query/{{ query.query_id }}" method="post" class="d-inline">
                                            <button type="submit" class="btn btn-sm btn-outline-danger" 
                                                    onclick="return confirm('Are you sure?')">
                                                <i class="bi bi-trash"></i> Remove
                                            </button>
                                        </form>
                                    </div>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>
```

## 🛍️ **Items (items.html)**

### **Фильтры (сворачиваемые)**
```html
<div class="row mb-4">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header d-flex align-items-center" data-bs-toggle="collapse" 
                 data-bs-target="#filterCollapse" style="cursor: pointer;">
                <i class="bi bi-funnel-fill me-2 text-info"></i>
                <h5 class="card-title mb-0">Filter Items</h5>
                <i class="bi bi-chevron-down ms-auto"></i>
            </div>
            <div class="collapse" id="filterCollapse">
                <div class="card-body">
                    <form action="/items" method="get">
                        <div class="row">
                            <div class="col-md-5">
                                <div class="form-group mb-3">
                                    <label for="query" class="form-label">Search by Query</label>
                                    <select class="form-select" id="query" name="query">
                                        <option value="">All Queries</option>
                                        {% for query in queries %}
                                        <option value="{{ query.query }}" 
                                                {% if selected_query == query.query %}selected{% endif %}>
                                            {{ query.display }}
                                        </option>
                                        {% endfor %}
                                    </select>
                                </div>
                            </div>
                            <div class="col-md-5">
                                <div class="form-group mb-3">
                                    <label for="limit" class="form-label">Number of Items</label>
                                    <select class="form-select" id="limit" name="limit">
                                        <option value="10" {% if limit == 10 %}selected{% endif %}>10 items</option>
                                        <option value="25" {% if limit == 25 %}selected{% endif %}>25 items</option>
                                        <option value="50" {% if limit == 50 %}selected{% endif %}>50 items</option>
                                        <option value="100" {% if limit == 100 %}selected{% endif %}>100 items</option>
                                        <option value="0" {% if limit == 0 %}selected{% endif %}>All items</option>
                                    </select>
                                </div>
                            </div>
                            <div class="col-md-2 d-flex align-items-center">
                                <button type="submit" class="btn btn-primary w-100">
                                    <i class="bi bi-search me-1"></i> Apply Filter
                                </button>
                            </div>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
```

### **Результаты товаров**
```html
<div class="row">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
                <div class="d-flex align-items-center">
                    <i class="bi bi-box-seam me-2 text-info"></i>
                    <h5 class="card-title mb-0">
                        {% if selected_query %}
                            Items for query: <span class="text-info">{{ selected_query_display }}</span>
                        {% else %}
                            All Items
                        {% endif %}
                    </h5>
                </div>
                <div class="btn-group" role="group">
                    <button type="button" class="btn btn-sm btn-outline-primary" id="cardViewBtn">
                        <i class="bi bi-grid-3x3-gap-fill me-1"></i> Cards
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-primary" id="listViewBtn">
                        <i class="bi bi-list-ul me-1"></i> List
                    </button>
                </div>
            </div>
            
            <div class="card-body">
                <!-- Card View - увеличенные карточки -->
                <div class="row" id="cardView">
                    {% for item in items %}
                    <div class="col-md-4 col-lg-3 mb-4">
                        <div class="card h-100">
                            <!-- Кликабельное фото -->
                            <a href="{{ item.url }}" target="_blank" class="text-decoration-none">
                                <img src="{{ item.photo_url }}" class="card-img-top" 
                                     style="aspect-ratio: 4/5; object-fit: cover;">
                            </a>
                            
                            <div class="card-body p-3">
                                <h6 class="card-title mb-2">{{ item.title }}</h6>
                                <p class="card-text mb-1">
                                    <span class="fw-bold text-dark">{{ item.price }} {{ item.currency }}</span>
                                    {% if item.brand_title %}
                                    <br><small class="text-muted">{{ item.brand_title }}</small>
                                    {% endif %}
                                </p>
                                <p class="card-text small text-muted mb-0">
                                    <i class="bi bi-clock me-1"></i> 
                                    <span class="badge bg-info">{{ item.timestamp }}</span>
                                </p>
                            </div>
                            
                            <div class="card-footer bg-white p-3">
                                <a href="{{ item.url }}" target="_blank" class="btn btn-primary w-100">
                                    View
                                </a>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>

                <!-- List View -->
                <div class="table-responsive" id="listView" style="display: none;">
                    <table class="table table-hover mb-0">
                        <thead>
                            <tr>
                                <th>Image</th>
                                <th>Title</th>
                                <th>Price</th>
                                <th>Query</th>
                                <th>Date</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for item in items %}
                            <tr>
                                <td style="width: 60px;">
                                    <img src="{{ item.photo_url }}" class="img-thumbnail"
                                         style="width: 50px; height: 50px; object-fit: cover;">
                                </td>
                                <td>{{ item.title }}</td>
                                <td>
                                    {{ item.price }} {{ item.currency }}
                                    {% if item.brand_title %}
                                    <br><small class="text-muted">{{ item.brand_title }}</small>
                                    {% endif %}
                                </td>
                                <td>{{ item.query|truncate(30) }}</td>
                                <td><span class="badge bg-success">{{ item.timestamp }}</span></td>
                                <td>
                                    <a href="{{ item.url }}" target="_blank" class="btn btn-sm btn-primary">
                                        View
                                    </a>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>
```

### **Auto-refresh JavaScript**
```javascript
<script>
// Auto-refresh каждые 10 секунд
setInterval(function() {
    if (document.visibilityState === 'visible') {
        const currentUrl = window.location.href;
        window.location.href = currentUrl;
    }
}, 10000);

// Cards/List view toggle с сохранением в localStorage
const cardViewBtn = document.getElementById('cardViewBtn');
const listViewBtn = document.getElementById('listViewBtn');
const cardView = document.getElementById('cardView');
const listView = document.getElementById('listView');

// Load saved preference
const viewPreference = localStorage.getItem('vintedViewPreference') || 'card';
setActiveView(viewPreference);

cardViewBtn.addEventListener('click', () => setActiveView('card'));
listViewBtn.addEventListener('click', () => setActiveView('list'));

function setActiveView(view) {
    if (view === 'card') {
        cardView.style.display = 'flex';
        listView.style.display = 'none';
        cardViewBtn.classList.add('active');
        listViewBtn.classList.remove('active');
        localStorage.setItem('vintedViewPreference', 'card');
    } else {
        cardView.style.display = 'none';
        listView.style.display = 'block';
        listViewBtn.classList.add('active');
        cardViewBtn.classList.remove('active');
        localStorage.setItem('vintedViewPreference', 'list');
    }
}
</script>
```

## ⚙️ **Configuration (config.html)**

### **Telegram Bot Settings**
```html
<div class="row mb-4">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5><i class="bi bi-telegram me-2"></i>Telegram Bot</h5>
            </div>
            <div class="card-body">
                <div class="mb-3">
                    <label for="telegram_token" class="form-label">Bot Token</label>
                    <input type="password" class="form-control" id="telegram_token" 
                           name="telegram_token" value="{{ params.telegram_token or '' }}">
                </div>
                <div class="mb-3">
                    <label for="telegram_chat_id" class="form-label">Chat ID</label>
                    <input type="text" class="form-control" id="telegram_chat_id" 
                           name="telegram_chat_id" value="{{ params.telegram_chat_id or '' }}">
                </div>
                
                <!-- Process Control в этой секции -->
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <span class="badge bg-{{ 'success' if telegram_running else 'secondary' }}">
                            {{ 'Running' if telegram_running else 'Stopped' }}
                        </span>
                    </div>
                    <div>
                        {% if telegram_running %}
                        <button class="btn btn-sm btn-danger process-control" 
                                data-process="telegram" data-action="stop">
                            <i class="bi bi-stop-fill"></i> Stop
                        </button>
                        {% else %}
                        <button class="btn btn-sm btn-success process-control" 
                                data-process="telegram" data-action="start">
                            <i class="bi bi-play-fill"></i> Start
                        </button>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Country Allowlist -->
    <div class="col-md-6">
        <div class="card allowlist-container">
            <div class="card-header">
                <h5><i class="bi bi-globe me-2"></i>Country Allowlist</h5>
            </div>
            <div class="card-body">
                <div class="mb-3">
                    <div class="input-group">
                        <input type="text" class="form-control" id="newCountry" 
                               placeholder="Enter country code (e.g., DE, FR, US)">
                        <button class="btn btn-outline-primary" type="button" onclick="addCountry()">
                            <i class="bi bi-plus"></i> Add
                        </button>
                    </div>
                </div>
                
                {% if countries %}
                <div class="list-group list-group-flush">
                    {% for country in countries %}
                    <div class="list-group-item d-flex justify-content-between align-items-center">
                        <span>{{ country }}</span>
                        <button class="btn btn-sm btn-outline-danger" onclick="removeCountry('{{ country }}')">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                    {% endfor %}
                </div>
                <div class="mt-3">
                    <button class="btn btn-sm btn-outline-warning" onclick="clearAllowlist()">
                        <i class="bi bi-trash"></i> Clear All
                    </button>
                </div>
                {% else %}
                <div class="alert alert-info alert-sm">
                    <i class="bi bi-info-circle me-2"></i>
                    No countries in allowlist. All countries are allowed.
                </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>
```

### **Proxy Settings**
```html
<div class="row mb-4">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header">
                <h5><i class="bi bi-shield-lock me-2"></i>Proxy Settings</h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label for="proxy_list" class="form-label">Proxy List</label>
                            <textarea class="form-control" id="proxy_list" name="proxy_list" rows="8"
                                      placeholder="Enter proxies, one per line">{{ params.proxy_list or '' }}</textarea>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label for="proxy_list_link" class="form-label">Proxy List URL</label>
                            <input type="url" class="form-control" id="proxy_list_link" 
                                   name="proxy_list_link" value="{{ params.proxy_list_link or '' }}">
                        </div>
                        <div class="form-check mb-3">
                            <input class="form-check-input" type="checkbox" id="check_proxies" 
                                   name="check_proxies" {{ 'checked' if params.check_proxies == 'True' }}>
                            <label class="form-check-label" for="check_proxies">
                                Check Proxies Before Use
                            </label>
                        </div>
                        
                        <!-- Proxy Statistics -->
                        <div class="card bg-light">
                            <div class="card-body">
                                <h6 class="card-title">Proxy Status</h6>
                                <div id="proxyStatus">Loading...</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
```

### **Railway Auto-Redeploy System**
```html
<div class="row mb-4">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header">
                <h5><i class="bi bi-arrow-repeat me-2"></i>Railway Auto-Redeploy System</h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-8">
                        <!-- Error Statistics -->
                        <div class="row mb-3">
                            <div class="col-md-3">
                                <div class="card bg-warning text-dark">
                                    <div class="card-body text-center p-2">
                                        <h6 class="card-title">401 Errors</h6>
                                        <h4 id="error401Count">-</h4>
                                        <small id="error401Time">-</small>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card bg-danger text-white">
                                    <div class="card-body text-center p-2">
                                        <h6 class="card-title">403 Errors</h6>
                                        <h4 id="error403Count">-</h4>
                                        <small id="error403Time">-</small>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card bg-info text-white">
                                    <div class="card-body text-center p-2">
                                        <h6 class="card-title">429 Errors</h6>
                                        <h4 id="error429Count">-</h4>
                                        <small id="error429Time">-</small>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card bg-dark text-white">
                                    <div class="card-body text-center p-2">
                                        <h6 class="card-title">Total Errors</h6>
                                        <h4 id="totalErrors">-</h4>
                                        <small>Combined</small>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label for="max_http_errors" class="form-label">Min HTTP Errors</label>
                            <input type="number" class="form-control" id="max_http_errors" 
                                   name="max_http_errors" value="{{ params.max_http_errors or 3 }}">
                        </div>
                        <div class="mb-3">
                            <label for="redeploy_time_window" class="form-label">Time Window (minutes)</label>
                            <input type="number" class="form-control" id="redeploy_time_window" 
                                   name="redeploy_time_window" value="{{ params.redeploy_time_window or 4 }}">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Last Redeploy</label>
                            <div class="form-control-plaintext" id="lastRedeploy">-</div>
                        </div>
                        <button type="button" class="btn btn-warning w-100" id="forceRedeployBtn">
                            <i class="bi bi-arrow-clockwise me-1"></i>Force Redeploy
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
```

### **General Settings & Save**
```html
<div class="row mb-4">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5><i class="bi bi-gear me-2"></i>General Settings</h5>
            </div>
            <div class="card-body">
                <div class="mb-3">
                    <label for="items_per_query" class="form-label">Items per Query</label>
                    <input type="number" class="form-control" id="items_per_query" 
                           name="items_per_query" value="{{ params.items_per_query or 20 }}">
                </div>
                <div class="mb-3">
                    <label for="query_refresh_delay" class="form-label">Query Refresh Delay (seconds)</label>
                    <input type="number" class="form-control" id="query_refresh_delay" 
                           name="query_refresh_delay" value="{{ params.query_refresh_delay or 60 }}">
                </div>
            </div>
        </div>
    </div>
    <div class="col-md-6 d-flex align-items-end">
        <button type="submit" class="btn btn-success btn-lg w-100">
            <i class="bi bi-check-circle me-2"></i>Save Configuration
        </button>
    </div>
</div>
```

### **JavaScript для AJAX операций**
```javascript
<script>
// Country Allowlist Management
function addCountry() {
    const country = document.getElementById('newCountry').value.trim();
    if (country) {
        fetch('/add_country', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `country=${encodeURIComponent(country)}`
        }).then(() => location.reload());
    }
}

function removeCountry(country) {
    fetch('/remove_country', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `country=${encodeURIComponent(country)}`
    }).then(() => location.reload());
}

// Force Redeploy
document.getElementById('forceRedeployBtn').addEventListener('click', function() {
    if (confirm('Are you sure you want to force redeploy?')) {
        fetch('/force_redeploy', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
                updateRedeployStatus();
            });
    }
});

// Update status displays
function updateRedeployStatus() {
    fetch('/redeploy_status')
        .then(response => response.json())
        .then(data => {
            document.getElementById('error401Count').textContent = data.error_401_count || 0;
            document.getElementById('error403Count').textContent = data.error_403_count || 0;
            document.getElementById('error429Count').textContent = data.error_429_count || 0;
            document.getElementById('totalErrors').textContent = data.total_errors || 0;
            document.getElementById('lastRedeploy').textContent = data.last_redeploy_time || 'Never';
        });
}

// Auto-update status every 30 seconds
setInterval(updateRedeployStatus, 30000);
updateRedeployStatus(); // Initial load
</script>
```

## 📋 **Logs (logs.html)**

### **Log Viewer Interface**
```html
<div class="row mb-4">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5><i class="bi bi-file-text me-2"></i>System Logs</h5>
                <div class="btn-group">
                    <button class="btn btn-sm btn-outline-primary" onclick="refreshLogs()">
                        <i class="bi bi-arrow-clockwise"></i> Refresh
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" onclick="downloadLogs()">
                        <i class="bi bi-download"></i> Download
                    </button>
                </div>
            </div>
            <div class="card-body">
                <!-- Log Filters -->
                <div class="row mb-3">
                    <div class="col-md-3">
                        <select class="form-select" id="logLevel">
                            <option value="">All Levels</option>
                            <option value="INFO">INFO</option>
                            <option value="WARNING">WARNING</option>
                            <option value="ERROR">ERROR</option>
                        </select>
                    </div>
                    <div class="col-md-6">
                        <input type="text" class="form-control" id="logSearch" 
                               placeholder="Search logs...">
                    </div>
                    <div class="col-md-3">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="autoRefresh">
                            <label class="form-check-label" for="autoRefresh">
                                Auto-refresh
                            </label>
                        </div>
                    </div>
                </div>
                
                <!-- Log Display -->
                <div class="bg-dark text-light p-3 rounded" style="height: 500px; overflow-y: auto; font-family: monospace;">
                    <div id="logContent">
                        <!-- Log entries will be loaded here -->
                        <div class="text-muted">Loading logs...</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
```

## 🎨 **Custom CSS (custom.css)**

```css
/* Card View Optimizations */
#cardView .card-img-top {
    width: 100%;
    aspect-ratio: 4/5;
    object-fit: cover;
}

#cardView .card-img-top.bg-light {
    width: 100%;
    aspect-ratio: 4/5;
}

/* Allowlist Compact Styling */
.allowlist-container .list-group-item {
    padding: 0.5rem 1rem;
}

.allowlist-container .alert-sm {
    padding: 0.5rem 0.75rem;
    font-size: 0.875rem;
}

/* Mobile Responsive */
@media (max-width: 768px) {
    .table-responsive {
        font-size: 0.85rem;
    }
    
    .btn-group .btn {
        font-size: 0.75rem;
        padding: 0.25rem 0.5rem;
    }
    
    .card-body {
        padding: 1rem 0.75rem;
    }
    
    .input-group-sm .form-control {
        font-size: 0.8rem;
    }
    
    .navbar-nav .nav-link {
        padding: 0.5rem 0.75rem;
        text-align: center;
    }
    
    .container-fluid {
        padding-left: 0.5rem;
        padding-right: 0.5rem;
    }
}

/* Loading States */
.loading {
    opacity: 0.6;
    pointer-events: none;
}

/* Toast Notifications */
.toast-container {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 1050;
}
```

## 🔧 **Ключевые особенности текущего интерфейса**

### **Технологии**
- **Backend**: Python Flask
- **Frontend**: Bootstrap 5.3.0 + Bootstrap Icons
- **Database**: PostgreSQL (Railway) / SQLite (локально)
- **Автообновление**: JavaScript setInterval каждые 10 секунд
- **Адаптивность**: Bootstrap responsive classes

### **Функциональные особенности**
- **Auto-migration**: Автоматическое добавление колонок в БД
- **Cards/List toggle**: Переключение видов с сохранением в localStorage
- **AJAX операции**: Управление allowlist без перезагрузки страницы
- **Modal confirmations**: Подтверждения для опасных операций
- **Flash messages**: Уведомления об успехе/ошибках
- **Collapsible filters**: Сворачиваемые фильтры на странице Items
- **Process control**: Управление Telegram ботом
- **Proxy management**: Проверка и управление прокси-серверами
- **Railway integration**: Автоматический редеплой при ошибках

### **UX паттерны**
- **Цветовое кодирование**: Зеленый = успех, красный = ошибка, синий = информация
- **Иконки**: Bootstrap Icons для всех действий
- **Badges**: Статусы и счетчики
- **Progress indicators**: Спиннеры для загрузки
- **Consistent spacing**: Bootstrap spacing utilities
- **Mobile-first**: Адаптивная сетка и компоненты