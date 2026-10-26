import Header from "./components/Header.jsx";
import AuthPage from "./pages/AuthPage.jsx";
import HomePage from "./pages/HomePage.jsx";
import { useRoute } from "./router.js";

export default function App() {
  const path = useRoute();

  return (
    <>
      <Header />
      <main className="container">{path === "/login" ? <AuthPage /> : <HomePage />}</main>
    </>
  );
}
