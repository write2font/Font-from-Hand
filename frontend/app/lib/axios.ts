import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8080/api/v1",
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
};

export default api;
