# RestroDine Data Layer

Synthetic educational restaurant data for RestroDine.

Period: 2025-01-01 to 2025-12-31.

Tables:
customers, products, employees, shifts, orders, order_items, payments,
promotions, calendar, weather.

The transactions use business rules rather than independent random values:
weekends/holidays increase demand, rainy days reduce demand, lunch/dinner
peaks are represented, and realistic product combinations are simulated.

The initial weather table is synthetic. Later it can be augmented/replaced
with historical weather API data for the forecasting experiment.
