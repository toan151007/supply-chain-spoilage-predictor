import { Route, Routes } from 'react-router-dom'

import Chatbot from './components/common/Chatbot.jsx'
import RealtimeAlerts from './components/common/RealtimeAlerts.jsx'
import Layout from './components/layout/Layout.jsx'
import ProtectedRoute from './components/layout/ProtectedRoute.jsx'
import AlertsPage from './pages/AlertsPage.jsx'
import CategoriesPage from './pages/CategoriesPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import ForecastsPage from './pages/ForecastsPage.jsx'
import InventoryPage from './pages/InventoryPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import NotFoundPage from './pages/NotFoundPage.jsx'
import OrdersPage from './pages/OrdersPage.jsx'
import ProductsPage from './pages/ProductsPage.jsx'
import StoresPage from './pages/StoresPage.jsx'

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route index element={<DashboardPage />} />
            <Route path="products" element={<ProductsPage />} />
            <Route path="inventory" element={<InventoryPage />} />
            <Route path="orders" element={<OrdersPage />} />
            <Route path="alerts" element={<AlertsPage />} />
            <Route path="forecasts" element={<ForecastsPage />} />
            <Route path="categories" element={<CategoriesPage />} />
            <Route path="stores" element={<StoresPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Route>
      </Routes>
      <Chatbot />
      <RealtimeAlerts />
    </>
  )
}
