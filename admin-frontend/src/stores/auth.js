import { defineStore } from "pinia";
import { adminLogin } from "../services/api";

const TOKEN_KEY = "admin_token";
const USER_KEY = "admin_user";

export const useAuthStore = defineStore("admin-auth", {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || "",
    username: localStorage.getItem(USER_KEY) || ""
  }),
  actions: {
    async login(username, password) {
      const data = await adminLogin(username, password);
      this.token = data.access_token;
      this.username = data.username;
      localStorage.setItem(TOKEN_KEY, this.token);
      localStorage.setItem(USER_KEY, this.username);
    },
    logout() {
      this.token = "";
      this.username = "";
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    }
  }
});

