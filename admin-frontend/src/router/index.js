import { createRouter, createWebHistory } from "vue-router";
import LoginPage from "../views/LoginPage.vue";
import AdminLayout from "../views/AdminLayout.vue";
import DashboardPage from "../views/DashboardPage.vue";
import PapersPage from "../views/PapersPage.vue";
import UsersPage from "../views/UsersPage.vue";
import JobsPage from "../views/JobsPage.vue";
import PaperEditPage from "../views/PaperEditPage.vue";
import AuditLogsPage from "../views/AuditLogsPage.vue";
import PermissionsPage from "../views/PermissionsPage.vue";
import ReviewsPage from "../views/ReviewsPage.vue";
import { useAuthStore } from "../stores/auth";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: LoginPage },
    {
      path: "/",
      component: AdminLayout,
      children: [
        { path: "", redirect: "/dashboard" },
        { path: "dashboard", component: DashboardPage },
        { path: "papers", component: PapersPage },
        { path: "papers/:id", component: PaperEditPage },
        { path: "users", component: UsersPage },
        { path: "permissions", component: PermissionsPage },
        { path: "reviews", component: ReviewsPage },
        { path: "jobs", component: JobsPage },
        { path: "audit-logs", component: AuditLogsPage }
      ]
    }
  ]
});

router.beforeEach((to) => {
  const auth = useAuthStore();
  if (to.path === "/login") {
    if (auth.token) return "/dashboard";
    return true;
  }
  if (!auth.token) return "/login";
  return true;
});

export default router;
