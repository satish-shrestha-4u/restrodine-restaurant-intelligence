CREATE DATABASE IF NOT EXISTS restrodine
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE restrodine;

SET FOREIGN_KEY_CHECKS = 0;

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
DROP TABLE IF EXISTS categories;

SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE customers (
    customer_id VARCHAR(16) PRIMARY KEY,
    customer_name VARCHAR(120) NOT NULL,
    age SMALLINT UNSIGNED,
    gender VARCHAR(32),
    city VARCHAR(100),
    registration_date DATE NOT NULL,
    customer_type VARCHAR(32),
    first_order_date DATE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Shared lookup keeps product and promotion categories linked consistently.
CREATE TABLE categories (
    category_name VARCHAR(60) PRIMARY KEY
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE products (
    product_id VARCHAR(16) PRIMARY KEY,
    category VARCHAR(60) NOT NULL,
    product_name VARCHAR(120) NOT NULL,
    selling_price DECIMAL(10,2) NOT NULL CHECK (selling_price >= 0),
    product_cost DECIMAL(10,2) NOT NULL CHECK (product_cost >= 0),
    active TINYINT NOT NULL CHECK (active IN (0,1)),
    CONSTRAINT fk_products_category
        FOREIGN KEY (category) REFERENCES categories(category_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE employees (
    employee_id VARCHAR(16) PRIMARY KEY,
    employee_name VARCHAR(120) NOT NULL,
    role VARCHAR(60) NOT NULL,
    employment_type VARCHAR(32) NOT NULL,
    hourly_cost DECIMAL(10,2) NOT NULL CHECK (hourly_cost >= 0),
    employment_start DATE NOT NULL,
    employment_end DATE,
    employment_status VARCHAR(32) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE calendar (
    date DATE PRIMARY KEY,
    day_of_week VARCHAR(16) NOT NULL,
    day_of_week_num TINYINT UNSIGNED NOT NULL,
    month TINYINT UNSIGNED NOT NULL CHECK (month BETWEEN 1 AND 12),
    month_name VARCHAR(16) NOT NULL,
    quarter TINYINT UNSIGNED NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    week_of_year SMALLINT UNSIGNED,
    is_weekend TINYINT NOT NULL CHECK (is_weekend IN (0,1)),
    restaurant_peak_day TINYINT NOT NULL CHECK (restaurant_peak_day IN (0,1)),
    restaurant_day_type VARCHAR(32) NOT NULL,
    holiday_name VARCHAR(120),
    is_holiday TINYINT NOT NULL CHECK (is_holiday IN (0,1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE weather (
    date DATE PRIMARY KEY,
    temperature_c DECIMAL(6,2) NOT NULL,
    precipitation_mm DECIMAL(8,2) NOT NULL CHECK (precipitation_mm >= 0),
    is_rainy TINYINT NOT NULL CHECK (is_rainy IN (0,1)),
    weather_condition VARCHAR(40) NOT NULL,
    CONSTRAINT fk_weather_calendar
        FOREIGN KEY (date) REFERENCES calendar(date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE promotions (
    promotion_id VARCHAR(16) PRIMARY KEY,
    promotion_name VARCHAR(120) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    discount_percentage DECIMAL(5,2) NOT NULL
        CHECK (discount_percentage BETWEEN 0 AND 100),
    product_category VARCHAR(60),
    CONSTRAINT fk_promotions_category
        FOREIGN KEY (product_category) REFERENCES categories(category_name),
    CONSTRAINT fk_promotions_start_date
        FOREIGN KEY (start_date) REFERENCES calendar(date),
    CONSTRAINT fk_promotions_end_date
        FOREIGN KEY (end_date) REFERENCES calendar(date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE employee_availability (
    employee_id VARCHAR(16) NOT NULL,
    day_of_week_num TINYINT UNSIGNED NOT NULL
        CHECK (day_of_week_num BETWEEN 0 AND 6),
    day_of_week VARCHAR(16) NOT NULL,
    availability_status VARCHAR(32) NOT NULL,
    max_hours DECIMAL(5,2) NOT NULL CHECK (max_hours >= 0),
    PRIMARY KEY (employee_id, day_of_week_num),
    CONSTRAINT fk_availability_employee
        FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE shifts (
    shift_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(16) NOT NULL,
    shift_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    hours_worked DECIMAL(5,2) NOT NULL CHECK (hours_worked >= 0),
    labour_cost DECIMAL(10,2) NOT NULL CHECK (labour_cost >= 0),
    CONSTRAINT fk_shifts_employee
        FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
    CONSTRAINT fk_shifts_calendar
        FOREIGN KEY (shift_date) REFERENCES calendar(date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE orders (
    order_id VARCHAR(20) PRIMARY KEY,
    customer_id VARCHAR(16),
    order_datetime DATETIME NOT NULL,
    order_date DATE NOT NULL,
    order_type VARCHAR(32) NOT NULL,
    meal_period VARCHAR(32) NOT NULL,
    order_total DECIMAL(10,2) NOT NULL CHECK (order_total >= 0),
    CONSTRAINT fk_orders_customer
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    CONSTRAINT fk_orders_calendar
        FOREIGN KEY (order_date) REFERENCES calendar(date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE order_items (
    order_item_id VARCHAR(24) PRIMARY KEY,
    order_id VARCHAR(20) NOT NULL,
    product_id VARCHAR(16) NOT NULL,
    quantity INT UNSIGNED NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(10,2) NOT NULL CHECK (unit_price >= 0),
    discount DECIMAL(10,2) NOT NULL CHECK (discount >= 0),
    line_total DECIMAL(10,2) NOT NULL CHECK (line_total >= 0),
    CONSTRAINT fk_order_items_order
        FOREIGN KEY (order_id) REFERENCES orders(order_id),
    CONSTRAINT fk_order_items_product
        FOREIGN KEY (product_id) REFERENCES products(product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE payments (
    payment_id VARCHAR(24) PRIMARY KEY,
    order_id VARCHAR(20) NOT NULL UNIQUE,
    payment_method VARCHAR(40) NOT NULL,
    amount DECIMAL(10,2) NOT NULL CHECK (amount >= 0),
    CONSTRAINT fk_payments_order
        FOREIGN KEY (order_id) REFERENCES orders(order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE reviews (
    review_id VARCHAR(24) PRIMARY KEY,
    customer_id VARCHAR(16) NOT NULL,
    review_date DATE NOT NULL,
    rating TINYINT UNSIGNED NOT NULL CHECK (rating BETWEEN 1 AND 5),
    review_text TEXT NOT NULL,
    CONSTRAINT fk_reviews_customer
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    CONSTRAINT fk_reviews_calendar
        FOREIGN KEY (review_date) REFERENCES calendar(date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE daily_revenue (
    date DATE PRIMARY KEY,
    revenue DECIMAL(12,2) NOT NULL CHECK (revenue >= 0),
    orders INT UNSIGNED NOT NULL CHECK (orders >= 0),
    average_order_value DECIMAL(10,2) NOT NULL
        CHECK (average_order_value >= 0),
    CONSTRAINT fk_daily_revenue_calendar
        FOREIGN KEY (date) REFERENCES calendar(date),
    CONSTRAINT fk_daily_revenue_weather
        FOREIGN KEY (date) REFERENCES weather(date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_datetime ON orders(order_datetime);
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);
CREATE INDEX idx_shifts_employee ON shifts(employee_id);
CREATE INDEX idx_shifts_date ON shifts(shift_date);
CREATE INDEX idx_reviews_customer ON reviews(customer_id);
CREATE INDEX idx_reviews_date ON reviews(review_date);
CREATE INDEX idx_promotions_start_date ON promotions(start_date);
CREATE INDEX idx_promotions_end_date ON promotions(end_date);
