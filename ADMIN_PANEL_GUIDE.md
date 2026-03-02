# React Admin Panel - Complete Guide

Production-ready admin dashboard for VPN subscription management.

## Table of Contents

1. [Installation](#installation)
2. [Architecture](#architecture)
3. [Components](#components)
4. [Pages](#pages)
5. [API Integration](#api-integration)
6. [State Management](#state-management)
7. [Styling](#styling)
8. [Deployment](#deployment)

---

## Installation

### Prerequisites

- Node.js 16+
- npm or yarn

### Setup

```bash
cd admin-panel
npm install
```

### Development

```bash
npm run dev
```

Runs on `http://localhost:5173` with hot module replacement.

### Production Build

```bash
npm run build
npm run preview
```

Builds optimized version in `dist/` directory.

---

## Architecture

### Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Runtime | Node.js | 16+ |
| Framework | React | 18.2.0 |
| Build Tool | Vite | 5.0.0 |
| Routing | React Router | 6.20.0 |
| HTTP Client | Axios | 1.6.2 |
| State | Zustand | 4.4.1 |
| Data Fetching | TanStack Query | 5.28.0 |
| Styling | Tailwind CSS | 3.4.0 |
| Icons | Lucide React | 0.294.0 |
| Editor | React Quill | 2.0.0 |

### Project Structure

```
admin-panel/
├── src/
│   ├── api/              # API client modules
│   │   ├── client.js     # Axios instance with interceptors
│   │   ├── auth.js       # Authentication APIs
│   │   ├── users.js      # User management APIs
│   │   ├── subscriptions.js
│   │   ├── servers.js
│   │   ├── payments.js
│   │   ├── stats.js
│   │   └── settings.js
│   ├── components/       # Reusable components
│   │   ├── Layout.jsx    # Main layout wrapper
│   │   ├── Sidebar.jsx   # Navigation menu
│   │   ├── Header.jsx    # Top header with user info
│   │   ├── ProtectedRoute.jsx
│   │   ├── DataTable.jsx
│   │   ├── StatCard.jsx
│   │   ├── Modal.jsx
│   │   └── Toast.jsx
│   ├── pages/            # Page components
│   │   ├── Login.jsx
│   │   ├── Dashboard.jsx
│   │   ├── Users.jsx
│   │   ├── UserDetail.jsx
│   │   ├── Subscriptions.jsx
│   │   ├── Servers.jsx
│   │   ├── Payments.jsx
│   │   ├── Settings.jsx
│   │   ├── BotTexts.jsx
│   │   ├── Broadcast.jsx
│   │   └── PlanPrices.jsx
│   ├── store/            # Zustand stores
│   │   ├── authStore.js
│   │   └── uiStore.js
│   ├── styles/
│   │   └── globals.css
│   ├── App.jsx           # Main app component
│   └── main.jsx          # Entry point
├── index.html
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
└── package.json
```

---

## Components

### Layout Components

#### `Layout.jsx`
Main layout wrapper containing:
- Sidebar for navigation
- Header with user info and logout
- Main content area
- Toast notification container

#### `Sidebar.jsx`
Navigation menu with:
- Dashboard link
- Users, Subscriptions, Servers pages
- Payments, Settings pages
- Bot Messages, Broadcast, Plan Prices
- Active route highlighting
- Icon indicators

#### `Header.jsx`
Top bar with:
- Welcome message with user email
- Notification bell icon
- Logout button

#### `ProtectedRoute.jsx`
Route wrapper that:
- Checks authentication on mount
- Validates JWT token
- Fetches user profile
- Redirects to login if not authenticated
- Shows loading spinner during auth check

### Data Components

#### `DataTable.jsx`
Reusable table component:
- Configurable columns with custom renderers
- Pagination controls
- Loading state with spinner
- Empty state message
- Row click handlers
- Responsive horizontal scroll

Props:
```javascript
{
  columns: Array,           // Column definitions
  data: Array,             // Table rows
  loading: bool,           // Loading state
  pagination: Object,      // Pagination info
  onPageChange: Function,  // Page change handler
  onRowClick: Function,    // Row click handler
  rowKey: String          // Row identifier (default: 'id')
}
```

#### `StatCard.jsx`
Statistics display card:
- Title and value
- Optional trend indicator
- Color-coded icons
- Responsive grid layout

Props:
```javascript
{
  title: String,
  value: String|Number,
  icon: Component,
  trend: Number,          // +/- percentage
  color: String          // blue|green|red|purple
}
```

#### `Modal.jsx`
Reusable modal dialog:
- Title bar with close button
- Custom content area
- Submit/Cancel buttons
- Backdrop overlay
- Z-index layering

Props:
```javascript
{
  isOpen: bool,
  title: String,
  children: ReactNode,
  onClose: Function,
  onSubmit: Function,
  submitText: String      // default: 'Save'
}
```

#### `Toast.jsx`
Toast notification system:
- Auto-dismiss after 4 seconds
- Multiple simultaneous toasts
- Type indicators (success, error, info)
- Color-coded styling
- Manual close button

---

## Pages

### Login Page

**Path:** `/login`

Features:
- Email and password fields
- Icons from Lucide React
- Submit loading state
- Error display from API
- Redirect to dashboard on success

### Dashboard

**Path:** `/`

Components:
- 6 stat cards (users, subscriptions, revenue, servers, payments)
- Recent activity section
- Server status overview
- Real-time updates (30s refresh)
- Trend indicators

### Users

**Path:** `/users`

Features:
- Searchable user list
- Pagination (20 per page)
- User status badge
- Click row to view details
- Search input with debounce

### UserDetail

**Path:** `/users/:id`

Displays:
- User information (email, telegram, balance, status)
- Ban/unban button
- Add balance form
- Subscriptions list
- Recent payments
- Referral count and earnings

### Subscriptions

**Path:** `/subscriptions`

Features:
- List all subscriptions
- Filter by status (all, active, expired)
- Traffic usage display
- Extend subscription modal
- Pagination

### Servers

**Path:** `/servers`

CRUD Operations:
- View all servers
- Add new server with form
- Edit server details
- Delete server
- Toggle active status

Server Fields:
- Name, Country
- Host/IP, Port
- Panel URL, Credentials
- Inbound ID
- Bypass RU checkbox

### Payments

**Path:** `/payments`

Features:
- List all payments
- Filter by status (pending, approved, rejected)
- Date range filtering
- Approve/reject pending payments
- Payment details view
- Rejection reason form

### Settings

**Path:** `/settings`

Configuration:
- Bot token
- Webhook URL
- Min/max withdrawal amounts
- Referral percentage

### BotTexts

**Path:** `/bot-texts`

Features:
- Edit all bot message templates
- Key-value pair interface
- Rich text support (HTML)
- Live preview
- Save all messages

### Broadcast

**Path:** `/broadcast`

Features:
- Message composition textarea
- Character counter (5000 limit)
- Word counter
- Send to all users button
- Message preview
- Confirmation with send count

### PlanPrices

**Path:** `/plan-prices`

Features:
- Editable price table
- Plan rows (Solo, Family, etc.)
- Period columns (1 month, 3 months, 1 year)
- Direct cell editing
- Save all prices

---

## API Integration

### Axios Client Configuration

Located in `src/api/client.js`:

```javascript
const client = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json'
  }
})
```

### Request Interceptor

- Automatically adds JWT Bearer token from localStorage
- Runs before every request

### Response Interceptor

- Handles 401 Unauthorized responses
- Attempts to refresh token
- Retries original request with new token
- Clears auth on refresh failure
- Redirects to login

### API Modules

Each module (`auth.js`, `users.js`, etc.) exports an API object with methods:

```javascript
// Example: users.js
export const usersApi = {
  getUsers: async (page, limit, search) => { ... },
  getUser: async (id) => { ... },
  banUser: async (id) => { ... },
  addBalance: async (id, amount) => { ... },
  // ... more methods
}
```

### Error Handling

All API calls wrapped in try-catch:

```javascript
try {
  const data = await usersApi.getUsers(1, 20)
} catch (error) {
  showError(error.response?.data?.detail || 'Failed to load users')
}
```

### Data Caching

TanStack Query provides automatic caching:

```javascript
const { data, isLoading } = useQuery({
  queryKey: ['users', page, search],
  queryFn: () => usersApi.getUsers(page, 20, search),
  staleTime: 1000 * 60 * 5  // 5 minutes
})
```

---

## State Management

### Authentication Store (Zustand)

Located in `src/store/authStore.js`:

```javascript
export const authStore = create((set) => ({
  isAuthenticated: false,
  user: null,
  
  setUser: (user) => set({ user, isAuthenticated: !!user }),
  logout: () => set({ user: null, isAuthenticated: false })
}))
```

Usage:
```javascript
const user = authStore((state) => state.user)
const setUser = authStore((state) => state.setUser)
```

### UI Store (Zustand)

Located in `src/store/uiStore.js`:

```javascript
export const uiStore = create((set) => ({
  toasts: [],
  
  addToast: (message, type) => { ... },
  removeToast: (id) => { ... },
  clearToasts: () => { ... }
}))
```

Helper functions:
```javascript
import { showSuccess, showError, showInfo } from '../store/uiStore'

showSuccess('Operation completed')
showError('Something went wrong')
showInfo('Information message')
```

### TanStack Query

For server state management:

```javascript
const { data, isLoading, error, refetch } = useQuery({
  queryKey: ['users', page],
  queryFn: () => usersApi.getUsers(page),
  keepPreviousData: true,
  refetchOnWindowFocus: false
})
```

Mutations:

```javascript
const mutation = useMutation({
  mutationFn: (data) => usersApi.updateUser(data),
  onSuccess: () => {
    refetch()
    showSuccess('Updated')
  },
  onError: () => showError('Failed')
})
```

---

## Styling

### Tailwind CSS

Utility-first CSS framework with:
- Custom dark theme configuration
- Responsive breakpoints
- Pre-configured colors
- Custom spacing scale

### Dark Theme

All components use dark theme:
- Background: `bg-dark-900`, `bg-dark-800`
- Text: `text-white`, `text-gray-300`
- Borders: `border-dark-700`
- Hover: `hover:bg-dark-700`

### Custom Styles

Located in `src/styles/globals.css`:

```css
/* Input styling */
input[type="text"],
input[type="email"],
select,
textarea {
  @apply w-full px-3 py-2 bg-dark-700 border border-dark-600 
         rounded-lg text-white focus:outline-none 
         focus:border-blue-500;
}

/* Badge variants */
.badge-success { @apply bg-green-900 text-green-200; }
.badge-danger { @apply bg-red-900 text-red-200; }
.badge-warning { @apply bg-yellow-900 text-yellow-200; }
```

### Color Palette

```javascript
{
  dark: {
    900: '#111827',  // Darkest
    800: '#1f2937',
    700: '#374151',
    600: '#4b5563',
    500: '#6b7280',
    400: '#9ca3af',
    300: '#d1d5db',
    200: '#e5e7eb',
    100: '#f3f4f6',
    50: '#f9fafb'   // Lightest
  }
}
```

---

## Deployment

### Build Process

```bash
npm run build
```

Produces optimized `dist/` directory with:
- Minified JavaScript
- Optimized CSS
- Asset hashing for cache busting
- Source maps excluded

### Serving

#### Using Vite Preview

```bash
npm run preview
```

#### Using Static Server

```bash
npx serve dist
```

#### Using Nginx

```nginx
server {
    listen 80;
    root /var/www/admin-panel/dist;
    
    location / {
        try_files $uri /index.html;
    }
    
    location /api {
        proxy_pass http://api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### Using Docker

```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Environment Configuration

Production `.env.local`:

```env
VITE_API_URL=https://api.yourdomain.com/api
```

### Security Headers

Add to Nginx:

```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Strict-Transport-Security "max-age=31536000" always;
```

### Performance Optimization

- Code splitting handled by Vite
- CSS purging with Tailwind
- Asset minification
- Gzip compression in Nginx

### Monitoring

- Monitor API response times
- Check JavaScript console for errors
- Review browser DevTools Network tab
- Use Sentry for error tracking (optional)

---

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

---

## Troubleshooting

### API Not Found

Check proxy configuration in `vite.config.js`:

```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      rewrite: (path) => path
    }
  }
}
```

### Toast Notifications Not Showing

Ensure `Toast` component is in main `Layout`:

```jsx
<Toast />
```

### Authentication Token Expired

Token refresh happens automatically via interceptor. If not working:
1. Check localStorage has `refresh_token`
2. Verify API `/auth/refresh` endpoint
3. Check token expiration times

### Performance Issues

1. Check TanStack Query cache settings
2. Review large table pagination
3. Profile with Chrome DevTools
4. Check network requests in Network tab

---

## Contributing

When adding new pages:
1. Create page component in `src/pages/`
2. Add API module if needed in `src/api/`
3. Update routing in `src/App.jsx`
4. Add navigation link in `src/components/Sidebar.jsx`
5. Follow existing component patterns
6. Test with real API endpoints

---

## License

Proprietary - VPN Sales System
