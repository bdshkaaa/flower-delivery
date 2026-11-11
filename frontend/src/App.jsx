import Header from "./components/Header.jsx";
import AuthPage from "./pages/AuthPage.jsx";
import CartPage from "./pages/CartPage.jsx";
import CatalogPage from "./pages/CatalogPage.jsx";
import HomePage from "./pages/HomePage.jsx";
import OrderDonePage from "./pages/OrderDonePage.jsx";
import OrdersPage from "./pages/OrdersPage.jsx";
import OrderStatusPage from "./pages/OrderStatusPage.jsx";
import PaymentPage from "./pages/PaymentPage.jsx";
import { parseOrderRoute } from "./orderFlow.js";
import { useRoute } from "./router.js";

export default function App() {
  const path = useRoute();
  const orderRoute = parseOrderRoute(path);

  return (
    <>
      <Header />
      <main className="container">
        {orderRoute?.page === "pay" ? (
          <PaymentPage key={orderRoute.id} id={orderRoute.id} />
        ) : orderRoute?.page === "done" ? (
          <OrderDonePage key={orderRoute.id} id={orderRoute.id} />
        ) : orderRoute ? (
          <OrderStatusPage key={orderRoute.id} id={orderRoute.id} />
        ) : path === "/login" ? (
          <AuthPage />
        ) : path === "/catalog" ? (
          <CatalogPage />
        ) : path === "/cart" ? (
          <CartPage />
        ) : path === "/orders" ? (
          <OrdersPage />
        ) : (
          <HomePage />
        )}
      </main>
    </>
  );
}
