# Database Schema

## Users Table
The `users` table contains registered user information.
- `id`: Unique integer identifier.
- `name`: Full name of the user.
- `email`: User email address.
- `signup_date`: Date when user registered.

## Orders Table
The `orders` table tracks customer purchases.
- `id`: Unique order ID.
- `user_id`: Foreign key to `users.id`.
- `amount`: Total order value in USD.
- `status`: One of 'PENDING', 'SHIPPED', 'DELIVERED', 'CANCELLED'.
- `created_at`: Timestamp of order creation.
