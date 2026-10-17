-- RestroDine schema for MySQL 8 (MySQL Workbench). Data is SYNTHETIC (2024-01-01 .. 2025-12-31).
-- Run the whole script (lightning-bolt icon). It DROPS and recreates the `restrodine` database tables.

CREATE DATABASE IF NOT EXISTS restrodine CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE restrodine;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS categories, daily_model_table, review_aspect_labels, reviews, payments, order_items, orders, shifts,
    employee_availability, employees, customers, products, promotions, calendar, weather, daily_revenue;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE categories (
    category_name  VARCHAR(30) NOT NULL,
    PRIMARY KEY (category_name)
) ENGINE=InnoDB;

CREATE TABLE calendar (
    `date`               DATE NOT NULL,
    day_of_week          VARCHAR(10),
    day_of_week_num      INT,
    `month`              INT,
    month_name           VARCHAR(10),
    `quarter`            INT,
    week_of_year         INT,
    is_weekend           TINYINT,
    restaurant_peak_day  TINYINT,
    restaurant_day_type  VARCHAR(10),
    holiday_name         VARCHAR(40) NULL,
    is_holiday           TINYINT,
    PRIMARY KEY (`date`)
) ENGINE=InnoDB;

CREATE TABLE promotions (
    promotion_id         VARCHAR(10) NOT NULL,
    promotion_name       VARCHAR(60),
    start_date           DATE,
    end_date             DATE,
    discount_percentage  DECIMAL(5,2),
    product_category     VARCHAR(30),
    PRIMARY KEY (promotion_id),
    CONSTRAINT fk_promo_cat FOREIGN KEY (product_category) REFERENCES categories (category_name)
) ENGINE=InnoDB;

CREATE TABLE customers (
    customer_id        VARCHAR(10) NOT NULL,
    customer_name      VARCHAR(80),
    age                INT,
    gender             VARCHAR(10),
    city               VARCHAR(40),
    registration_date  DATE NOT NULL,
    customer_type      VARCHAR(20),
    first_order_date   DATE NULL,
    PRIMARY KEY (customer_id)
) ENGINE=InnoDB;

CREATE TABLE products (
    product_id     VARCHAR(10) NOT NULL,
    category       VARCHAR(30),
    product_name   VARCHAR(60),
    selling_price  DECIMAL(8,2),
    product_cost   DECIMAL(8,2),
    active         TINYINT,
    PRIMARY KEY (product_id),
    CONSTRAINT fk_prod_cat FOREIGN KEY (category) REFERENCES categories (category_name)
) ENGINE=InnoDB;

CREATE TABLE employees (
    employee_id        VARCHAR(10) NOT NULL,
    employee_name      VARCHAR(80),
    `role`             VARCHAR(40),
    employment_type    VARCHAR(20),
    hourly_cost        DECIMAL(6,2),
    employment_start   DATE,
    employment_end     DATE NULL,
    employment_status  VARCHAR(10),
    PRIMARY KEY (employee_id)
) ENGINE=InnoDB;

CREATE TABLE employee_availability (
    employee_id         VARCHAR(10) NOT NULL,
    day_of_week_num     INT NOT NULL,
    day_of_week         VARCHAR(10),
    availability_status VARCHAR(12),
    max_hours           DECIMAL(4,1),
    PRIMARY KEY (employee_id, day_of_week_num),
    CONSTRAINT fk_avail_emp FOREIGN KEY (employee_id) REFERENCES employees (employee_id)
) ENGINE=InnoDB;

CREATE TABLE shifts (
    shift_id       VARCHAR(10) NOT NULL,
    employee_id    VARCHAR(10) NOT NULL,
    shift_date     DATE,
    shift_type     VARCHAR(10),
    start_time     TIME,
    end_time       TIME,
    hours_worked   DECIMAL(4,1),
    labour_cost    DECIMAL(8,2),
    PRIMARY KEY (shift_id),
    KEY idx_shifts_date (shift_date),
    CONSTRAINT fk_shift_emp FOREIGN KEY (employee_id) REFERENCES employees (employee_id),
    CONSTRAINT fk_shift_date FOREIGN KEY (shift_date) REFERENCES calendar (`date`)
) ENGINE=InnoDB;

CREATE TABLE orders (
    order_id        VARCHAR(10) NOT NULL,
    customer_id     VARCHAR(10) NULL,            -- NULL = walk-in guest
    order_datetime  DATETIME NOT NULL,
    order_date      DATE NOT NULL,               -- = DATE(order_datetime), links to calendar
    order_type      VARCHAR(10),
    meal_period     VARCHAR(10),
    order_total     DECIMAL(8,2),
    party_size      INT,
    PRIMARY KEY (order_id),
    KEY idx_orders_datetime (order_datetime),
    KEY idx_orders_customer (customer_id),
    CONSTRAINT fk_orders_cust FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
    CONSTRAINT fk_orders_date FOREIGN KEY (order_date)  REFERENCES calendar (`date`)
) ENGINE=InnoDB;

CREATE TABLE order_items (
    order_item_id  VARCHAR(12) NOT NULL,
    order_id       VARCHAR(10) NOT NULL,
    product_id     VARCHAR(10) NOT NULL,
    quantity       INT,
    unit_price     DECIMAL(8,2),
    discount_pct   DECIMAL(5,2),                 -- percent, not euros
    line_total     DECIMAL(8,2),
    promotion_id   VARCHAR(10) NULL,             -- promotion that produced the discount
    PRIMARY KEY (order_item_id),
    KEY idx_items_order (order_id),
    KEY idx_items_product (product_id),
    CONSTRAINT fk_items_order   FOREIGN KEY (order_id)   REFERENCES orders (order_id),
    CONSTRAINT fk_items_product FOREIGN KEY (product_id) REFERENCES products (product_id),
    CONSTRAINT fk_items_promo   FOREIGN KEY (promotion_id) REFERENCES promotions (promotion_id)
) ENGINE=InnoDB;

CREATE TABLE payments (
    payment_id      VARCHAR(12) NOT NULL,
    order_id        VARCHAR(10) NOT NULL,
    payment_method  VARCHAR(15),
    amount          DECIMAL(8,2),
    PRIMARY KEY (payment_id),
    KEY idx_pay_order (order_id),
    CONSTRAINT fk_pay_order FOREIGN KEY (order_id) REFERENCES orders (order_id)
) ENGINE=InnoDB;

CREATE TABLE weather (
    `date`             DATE NOT NULL,
    temperature_c      DECIMAL(4,1),
    temp_max_c         DECIMAL(4,1),
    temp_min_c         DECIMAL(4,1),
    precipitation_mm   DECIMAL(5,1),
    is_rainy           TINYINT,
    weather_condition  VARCHAR(15),
    PRIMARY KEY (`date`),
    CONSTRAINT fk_weather_date FOREIGN KEY (`date`) REFERENCES calendar (`date`)
) ENGINE=InnoDB;

CREATE TABLE reviews (
    review_id    VARCHAR(10) NOT NULL,
    customer_id  VARCHAR(10) NOT NULL,
    order_id     VARCHAR(10) NOT NULL,
    review_date  DATE,
    rating       INT,
    review_text  TEXT,
    PRIMARY KEY (review_id),
    KEY idx_reviews_date (review_date),
    CONSTRAINT fk_rev_cust  FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
    CONSTRAINT fk_rev_order FOREIGN KEY (order_id)    REFERENCES orders (order_id),
    CONSTRAINT fk_rev_date  FOREIGN KEY (review_date) REFERENCES calendar (`date`)
) ENGINE=InnoDB;

CREATE TABLE review_aspect_labels (
    review_id  VARCHAR(10) NOT NULL,
    aspect     VARCHAR(20) NOT NULL,
    sentiment  VARCHAR(10),
    PRIMARY KEY (review_id, aspect),
    CONSTRAINT fk_aspect_review FOREIGN KEY (review_id) REFERENCES reviews (review_id)
) ENGINE=InnoDB;

CREATE TABLE daily_revenue (
    `date`               DATE NOT NULL,
    revenue              DECIMAL(10,2),
    orders               INT,
    average_order_value  DECIMAL(8,2),
    day_of_week          VARCHAR(10),
    day_of_week_num      INT,
    `month`              INT,
    month_name           VARCHAR(10),
    `quarter`            INT,
    week_of_year         INT,
    is_weekend           TINYINT,
    restaurant_peak_day  TINYINT,
    restaurant_day_type  VARCHAR(10),
    holiday_name         VARCHAR(40) NULL,
    is_holiday           TINYINT,
    temperature_c        DECIMAL(4,1),
    temp_max_c           DECIMAL(4,1),
    temp_min_c           DECIMAL(4,1),
    precipitation_mm     DECIMAL(5,1),
    is_rainy             TINYINT,
    weather_condition    VARCHAR(15),
    is_promo_day         TINYINT,
    PRIMARY KEY (`date`),
    CONSTRAINT fk_dr_cal     FOREIGN KEY (`date`) REFERENCES calendar (`date`),
    CONSTRAINT fk_dr_weather FOREIGN KEY (`date`) REFERENCES weather (`date`)
) ENGINE=InnoDB;

-- Model-ready daily table (daily_revenue + meal-period order counts + drink revenue).
CREATE TABLE daily_model_table (
    `date`               DATE NOT NULL,
    revenue              DECIMAL(10,2),
    orders               INT,
    average_order_value  DECIMAL(8,2),
    orders_lunch         INT,
    orders_afternoon     INT,
    orders_dinner        INT,
    drink_revenue        DECIMAL(10,2),
    day_of_week          VARCHAR(10),
    day_of_week_num      INT,
    `month`              INT,
    month_name           VARCHAR(10),
    `quarter`            INT,
    week_of_year         INT,
    is_weekend           TINYINT,
    restaurant_peak_day  TINYINT,
    restaurant_day_type  VARCHAR(10),
    holiday_name         VARCHAR(40) NULL,
    is_holiday           TINYINT,
    temperature_c        DECIMAL(4,1),
    temp_max_c           DECIMAL(4,1),
    temp_min_c           DECIMAL(4,1),
    precipitation_mm     DECIMAL(5,1),
    is_rainy             TINYINT,
    weather_condition    VARCHAR(15),
    is_promo_day         TINYINT,
    PRIMARY KEY (`date`),
    CONSTRAINT fk_dm_dr FOREIGN KEY (`date`) REFERENCES daily_revenue (`date`)
) ENGINE=InnoDB;
