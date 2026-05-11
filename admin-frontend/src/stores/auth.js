import { defineStore } from "pinia";
import { adminLogin, changePassword as apiChangePassword } from "../services/api";

const TOKEN_KEY = "admin_token";
const USER_KEY = "admin_user";
const MUST_CHANGE_PASSWORD_KEY = "admin_must_change_password";

export const useAuthStore = defineStore("admin-auth", {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || "",
    username: localStorage.getItem(USER_KEY) || "",
    mustChangePassword: localStorage.getItem(MUST_CHANGE_PASSWORD_KEY) === "true"
  }),
  actions: {
    async login(username, password) {
      const data = await adminLogin(username, password);
      const roles = data.role_codes || [];
      if (!roles.includes("admin")) {
        throw { detail: "该账号不是管理员，不能登录管理后台" };
      }
      this.token = data.access_token;
      this.username = data.username;
      this.mustChangePassword = !!data.must_change_password;
      localStorage.setItem(TOKEN_KEY, this.token);
      localStorage.setItem(USER_KEY, this.username);
      localStorage.setItem(MUST_CHANGE_PASSWORD_KEY, String(this.mustChangePassword));
    },
    async changePassword(currentPassword, newPassword) {
      await apiChangePassword(currentPassword, newPassword);
      this.mustChangePassword = false;
      localStorage.setItem(MUST_CHANGE_PASSWORD_KEY, "false");
    },
    logout() {
      this.token = "";
      this.username = "";
      this.mustChangePassword = false;
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      localStorage.removeItem(MUST_CHANGE_PASSWORD_KEY);
    }
  }
});
