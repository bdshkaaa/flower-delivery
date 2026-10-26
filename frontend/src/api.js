// Единая точка для запросов к backend. Адрес /api/* проксируется на сервер
// (nginx в docker-compose, vite в режиме разработки), префикс /api отбрасывается.

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

function messageFrom(data, status) {
  if (data && typeof data.detail === "string") return data.detail;
  if (status === 422) return "Проверьте правильность заполнения полей";
  return "Что-то пошло не так. Попробуйте ещё раз.";
}

export async function api(path, { method = "GET", body, token } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;

  let response;
  try {
    response = await fetch(`/api${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, "Нет связи с сервером. Попробуйте позже.");
  }

  if (response.status === 204) return null;
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(response.status, messageFrom(data, response.status));
  return data;
}
