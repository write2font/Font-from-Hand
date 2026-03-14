import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8080/api/v1",
  timeout: 10000,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("API 에러 발생:", error.response?.data || error.message);
    return Promise.reject(error);
  },
);

export default api;
