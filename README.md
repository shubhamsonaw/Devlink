# Devlink
The platform where peoples can share and solve their software problems and collaborate.
so make the connection that can help to hire and help to build something different.

## Run the full project with Docker

Requirements: Docker Desktop (Windows/macOS) or Docker Engine with Docker Compose (Linux). Python does not need to be installed on the host.

From the project folder, run:

```bash
docker compose up --build -d
```

Compose builds the Django app image, starts PostgreSQL and Redis, applies database migrations, then starts the site. Open `http://127.0.0.1:8001`. If that port is already in use, set `APP_PORT` to another free local port before starting. Check startup with `docker compose ps` and view app logs with `docker compose logs -f web`.

Redis serves two separate purposes: Django Channels uses Redis database 0 for WebSocket messaging, and Django's cache uses Redis database 1. The public homepage feed is cached for 60 seconds; user-specific page content is rendered per request. If Redis cache operations fail temporarily, the homepage falls back to PostgreSQL. To check the cache backend from the web container, run `docker compose exec web python manage.py shell -c "from django.core.cache import cache; cache.set('manual:probe', 'ok', 30); print(cache.get('manual:probe'))"`; it should print `ok`.

Stop the project with `docker compose down`. PostgreSQL data and uploaded media persist in Docker volumes. Do not use `docker compose down -v` unless you intentionally want to permanently erase both volumes. This setup is for local demos, not public internet deployment.

## JWT authentication in Postman

The website keeps its normal Django session login. API requests use short-lived JWT access tokens.

1. Send `POST http://127.0.0.1:8001/api/auth/token/` with **Body → raw → JSON**:

   ```json
   {"username": "your-username", "password": "your-password"}
   ```

   Copy the `access` and `refresh` values from the JSON response.
2. Send `GET http://127.0.0.1:8001/api/auth/me/` with **Authorization → Bearer Token**, using the `access` value. It expires after 60 minutes.
3. When it expires, send `POST http://127.0.0.1:8001/api/auth/token/refresh/` with JSON `{ "refresh": "your-refresh-token" }`. Save both returned tokens; refresh tokens rotate and the previous one is revoked.
4. To log out the API client, send `POST http://127.0.0.1:8001/api/auth/token/blacklist/` with JSON `{ "refresh": "your-current-refresh-token" }`.

Keep access and refresh tokens private. For a different API client, create a token using that user's own credentials.

### Create a problem with JWT

Use the API route below for Postman. `/problems/create/` is the website's HTML form and still requires a browser session and CSRF token.

1. Obtain an access token with `POST http://127.0.0.1:8001/api/auth/token/` and a raw JSON body containing your username and password, as described above.
2. Create a request with method `POST` and URL `http://127.0.0.1:8001/api/problems/`.
3. In **Authorization**, choose **Bearer Token** and paste the access token. Do not add an `X-CSRFToken` header to this API request.
4. In **Body**, choose **raw** and **JSON**, then send:

   ```json
   {
     "title": "Improve search results",
     "description": "Search should rank relevant problems first.",
     "difficulty": "medium",
     "tags": ["search", "backend"]
   }
   ```

A successful request returns **201 Created** with the new problem's details. The authenticated token owner is assigned as the problem author; the client cannot set `user` or `status`. Missing or invalid tokens return **401 Unauthorized**. Supported difficulties are `easy`, `medium`, and `hard`; tags are optional, with up to five names.
