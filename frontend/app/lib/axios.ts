import axios from "axios";

export const getApiBaseUrl = () => {
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL;
  }

  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.hostname}:8080/api/v1`;
  }

  return "http://localhost:8080/api/v1";
};

const api = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: 10000,
  withCredentials: true,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      return Promise.reject(error);
    }

    console.error("API 에러 발생:", error.response?.data || error.message);
    return Promise.reject(error);
  },
);

export const authService = {
  signIn: async (email: string, password: string) => {
    const response = await api.post("/auth/signin", { email, password });
    return response.data;
  },

  signUp: async (email: string, password: string, name: string) => {
    const response = await api.post("/auth/signup", { email, password, name });
    return response.data;
  },

  signOut: async () => {
    try {
      await api.post("/auth/signout");

      localStorage.removeItem("accessToken");

      window.location.href = "/";
    } catch (error) {
      console.error("로그아웃 중 에러:", error);
      window.location.href = "/";
    }
  },

  getMe: async () => {
    const response = await api.get("/auth/me");
    return response.data;
  },

  updateName: async (name: string) => {
    const response = await api.patch("/auth/me", { name });
    return response.data;
  },

  deleteAccount: async () => {
    await api.delete("/auth/me");
  },
};

export default api;
