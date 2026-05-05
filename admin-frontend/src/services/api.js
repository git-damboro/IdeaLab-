import http from "./http";

export const adminLogin = async (username, password) => {
  const formData = new URLSearchParams();
  formData.append("username", username);
  formData.append("password", password);
  const { data } = await http.post("/auth/login", formData, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" }
  });
  return data;
};

export const listAdminPapers = async ({ page = 1, pageSize = 20, keyword = "", status = "" } = {}) => {
  const { data } = await http.get("/api/v1/admin/papers", {
    params: { page, page_size: pageSize, keyword: keyword || undefined, status: status || undefined }
  });
  return data;
};

export const createAdminPaper = async (payload) => {
  const { data } = await http.post("/api/v1/admin/papers", payload);
  return data;
};

export const getAdminPaper = async (paperId) => {
  const { data } = await http.get(`/api/v1/admin/papers/${paperId}`);
  return data;
};

export const updateAdminPaper = async (paperId, payload) => {
  const { data } = await http.put(`/api/v1/admin/papers/${paperId}`, payload);
  return data;
};

export const publishAdminPaper = async (paperId) => {
  const { data } = await http.post(`/api/v1/admin/papers/${paperId}/publish`);
  return data;
};

export const offlineAdminPaper = async (paperId) => {
  const { data } = await http.post(`/api/v1/admin/papers/${paperId}/offline`);
  return data;
};

export const listAdminUsers = async ({ page = 1, pageSize = 20, keyword = "" } = {}) => {
  const { data } = await http.get("/api/v1/admin/users", {
    params: { page, page_size: pageSize, keyword: keyword || undefined }
  });
  return data;
};

export const listAdminRoles = async () => {
  const { data } = await http.get("/api/v1/admin/roles");
  return data;
};

export const updateAdminUserRoles = async (username, roleCodes) => {
  const { data } = await http.put(`/api/v1/admin/users/${username}/roles`, { role_codes: roleCodes });
  return data;
};

export const listAdminPermissions = async () => {
  const { data } = await http.get("/api/v1/admin/permissions");
  return data;
};

export const listAdminRolePermissions = async () => {
  const { data } = await http.get("/api/v1/admin/role-permissions");
  return data;
};

export const updateAdminRolePermissions = async (roleCode, permissions) => {
  const { data } = await http.put(`/api/v1/admin/role-permissions/${roleCode}`, { permissions });
  return data;
};

export const listAdminJobs = async ({ page = 1, pageSize = 20, status = "", jobType = "" } = {}) => {
  const { data } = await http.get("/api/v1/admin/jobs", {
    params: { page, page_size: pageSize, status: status || undefined, job_type: jobType || undefined }
  });
  return data;
};

export const createAdminJob = async (payload) => {
  const { data } = await http.post("/api/v1/admin/jobs", payload);
  return data;
};

export const uploadImportJob = async (file) => {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await http.post("/api/v1/admin/jobs/import-upload", formData, {
    headers: { "Content-Type": "multipart/form-data" }
  });
  return data;
};

export const retryAdminJob = async (jobId) => {
  const { data } = await http.post(`/api/v1/admin/jobs/${jobId}/retry`);
  return data;
};

export const getAdminJob = async (jobId) => {
  const { data } = await http.get(`/api/v1/admin/jobs/${jobId}`);
  return data;
};

export const updateAdminJobStatus = async (jobId, payload) => {
  const { data } = await http.put(`/api/v1/admin/jobs/${jobId}/status`, payload);
  return data;
};

export const getAdminOverview = async () => {
  const { data } = await http.get("/api/v1/admin/metrics/overview");
  return data;
};

export const getAdminTrend = async (days = 7) => {
  const { data } = await http.get("/api/v1/admin/metrics/trend", { params: { days } });
  return data;
};

export const listAdminAuditLogs = async ({ page = 1, pageSize = 20 } = {}) => {
  const { data } = await http.get("/api/v1/admin/audit-logs", {
    params: { page, page_size: pageSize }
  });
  return data;
};

export const getWorkflowOptions = async () => {
  const { data } = await http.get("/api/v1/admin/reviews/workflow-options");
  return data;
};

export const listReviewPipeline = async ({ page = 1, pageSize = 20, keyword = "", workflowStatus = "" } = {}) => {
  const { data } = await http.get("/api/v1/admin/reviews/pipeline", {
    params: {
      page,
      page_size: pageSize,
      keyword: keyword || undefined,
      workflow_status: workflowStatus || undefined
    }
  });
  return data;
};

export const transitionReviewWorkflow = async (paperId, payload) => {
  const { data } = await http.post(`/api/v1/admin/reviews/${paperId}/transition`, payload);
  return data;
};

export const listReviewRecords = async (paperId) => {
  const { data } = await http.get(`/api/v1/admin/reviews/${paperId}/records`);
  return data;
};
