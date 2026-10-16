PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS daily_revenue;
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS shifts;
DROP TABLE IF EXISTS employee_availability;
DROP TABLE IF EXISTS promotions;
DROP TABLE IF EXISTS weather;
DROP TABLE IF EXISTS calendar;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL,
    age INTEGER,
    gender TEXT,
    city TEXT,
    registration_date TEXT NOT NULL,
    customer_type TEXT,
    first_order_date TEXT
);

CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    product_name TEXT NOT NULL,
    selling_price REAL NOT NULL CHECK (selling_price >= 0),
    product_cost REAL NOT NULL CHECK (product_cost >= 0),
    active INTEGER NOT NULL CHECK (active IN (0,1))
);

CREATE TABLE employees (
    employee_id TEXT PRIMARY KEY,
    employee_name TEXT NOT NULL,
    role TEXT NOT NULL,
    employment_type TEXT NOT NULL,
    hourly_cost REAL NOT NULL CHECK (hourly_cost >= 0),
    employment_start TEXT NOT NULL,
    employment_end TEXT,
    employment_status TEXT NOT NULL
);

CREATE TABLE calendar (
    date TEXT PRIMARY KEY,
    day_of_week TEXT NOT NULL,
    day_of_week_num INTEGER NOT NULL,
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    month_name TEXT NOT NULL,
    quarter INTEGER NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    week_of_year REAL,
    is_weekend INTEGER NOT NULL CHECK (is_weekend IN (0,1)),
    restaurant_peak_day INTEGER NOT NULL CHECK (restaurant_peak_day IN (0,1)),
    restaurant_day_type TEXT NOT NULL,
    holiday_name TEXT,
    is_holiday INTEGER NOT NULL CHECK (is_holiday IN (0,1))
);

CREATE TABLE weather (
    date TEXT PRIMARY KEY,
    temperature_c REAL NOT NULL,
    precipitation_mm REAL NOT NULL CHECK (precipitation_mm >= 0),
    is_rainy INTEGER NOT NULL CHECK (is_rainy IN (0,1)),
    weather_condition TEXT NOT NULL
);

CREATE TABLE promotions (
    promotion_id TEXT PRIMARY KEY,
    promotion_name TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    discount_percentage REAL NOT NULL CHECK (discount_percentage BETWEEN 0 AND 100),
    product_category TEXT
);

CREATE TABLE employee_availability (
    employee_id TEXT NOT NULL,
    day_of_week_num INTEGER NOT NULL CHECK (day_of_week_num BETWEEN 0 AND 6),
    day_of_week TEXT NOT NULL,
    availability_status TEXT NOT NULL,
    max_hours REAL NOT NULL CHECK (max_hours >= 0),
    PRIMARY KEY (employee_id, day_of_week_num),
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
);

CREATE TABLE shifts (
    shift_id TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL,
    shift_date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    hours_worked REAL NOT NULL CHECK (hours_worked >= 0),
    labour_cost REAL NOT NULL CHECK (labour_cost >= 0),
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
);

CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT,
    order_datetime TEXT NOT NULL,
    order_type TEXT NOT NULL,
    meal_period TEXT NOT NULL,
    order_total REAL NOT NULL CHECK (order_total >= 0),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE order_items (
    order_item_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price REAL NOT NULL CHECK (unit_price >= 0),
    discount REAL NOT NULL CHECK (discount >= 0),
    line_total REAL NOT NULL CHECK (line_total >= 0),
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE payments (
    payment_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL UNIQUE,
    payment_method TEXT NOT NULL,
    amount REAL NOT NULL CHECK (amount >= 0),
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

CREATE TABLE reviews (
    review_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    review_date TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    review_text TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE daily_revenue (
    date TEXT PRIMARY KEY,
    revenue REAL NOT NULL CHECK (revenue >= 0),
    orders INTEGER NOT NULL CHECK (orders >= 0),
    average_order_value REAL NOT NULL CHECK (average_order_value >= 0),
    day_of_week TEXT NOT NULL,
    day_of_week_num INTEGER NOT NULL,
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    month_name TEXT NOT NULL,
    quarter INTEGER NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    week_of_year REAL,
    is_weekend INTEGER NOT NULL CHECK (is_weekend IN (0,1)),
    restaurant_peak_day INTEGER NOT NULL CHECK (restaurant_peak_day IN (0,1)),
    restaurant_day_type TEXT NOT NULL,
    holiday_name TEXT,
    is_holiday INTEGER NOT NULL CHECK (is_holiday IN (0,1)),
    temperature_c REAL NOT NULL,
    precipitation_mm REAL NOT NULL CHECK (precipitation_mm >= 0),
    is_rainy INTEGER NOT NULL CHECK (is_rainy IN (0,1)),
    weather_condition TEXT NOT NULL
);

CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_datetime ON orders(order_datetime);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);
CREATE INDEX idx_payments_order ON payments(order_id);
CREATE INDEX idx_shifts_employee ON shifts(employee_id);
CREATE INDEX idx_shifts_date ON shifts(shift_date);
CREATE INDEX idx_reviews_customer ON reviews(customer_id);
CREATE INDEX idx_reviews_date ON reviews(review_date);
