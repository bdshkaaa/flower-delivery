import Header from "./components/Header.jsx";
import AuthPage from "./pages/AuthPage.jsx";
import CartPage from "./pages/CartPage.jsx";
import CatalogPage from "./pages/CatalogPage.jsx";
import HomePage from "./pages/HomePage.jsx";
import OrdersPage from "./pages/OrdersPage.jsx";
import { useRoute } from "./router.js";

export default function App() {
  const path = useRoute();

  return (
    <>
      <Header />
      <main className="container">
        {path === "/login" ? (
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
