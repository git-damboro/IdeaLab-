<template>
  <div>
    <div class="page-head">
      <h2>任务中心</h2>
      <div class="actions">
        <el-select v-model="statusFilter" clearable placeholder="状态" style="width: 140px">
          <el-option label="排队中" value="queued" />
          <el-option label="运行中" value="running" />
          <el-option label="成功" value="success" />
          <el-option label="失败" value="failed" />
          <el-option label="已取消" value="canceled" />
        </el-select>
        <el-select v-model="typeFilter" clearable placeholder="类型" style="width: 140px">
          <el-option label="导入" value="import" />
          <el-option label="重建索引" value="reindex" />
          <el-option label="摘要生成" value="summary" />
        </el-select>
        <el-button type="primary" @click="loadJobs">搜索</el-button>
        <el-button @click="showCreate = true">新建任务</el-button>
      </div>
    </div>

    <el-card class="upload-card">
      <div class="upload-title">上传导入文件（.bib/.csv/.json）</div>
      <div class="upload-row">
        <input type="file" ref="fileInput" @change="onFileChange" accept=".bib,.csv,.json" />
        <el-button type="success" :loading="uploading" @click="uploadFile">上传并入队</el-button>
      </div>
      <div v-if="selectedFile" class="hint">已选文件：{{ selectedFile.name }}</div>
    </el-card>

    <el-table :data="rows" border v-loading="loading" @row-click="openJobDetail">
      <el-table-column prop="job_id" label="任务ID" min-width="220" />
      <el-table-column label="类型" width="120">
        <template #default="{ row }">{{ mapJobType(row.type) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="{ row }">{{ mapJobStatus(row.status) }}</template>
      </el-table-column>
      <el-table-column label="进度" width="180">
        <template #default="{ row }"><el-progress :percentage="Number(row.progress || 0)" /></template>
      </el-table-column>
      <el-table-column label="结果" min-width="200">
        <template #default="{ row }">
          <span v-if="row.result">新增 {{ row.result.inserted || 0 }} / 总计 {{ row.result.total || 0 }}</span>
          <span v-else>{{ row.error || "-" }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="230">
        <template #default="{ row }">
          <el-button size="small" type="primary" @click.stop="refreshOne(row)">刷新</el-button>
          <el-button
            size="small"
            type="warning"
            plain
            :disabled="![`failed`, `canceled`].includes(row.status)"
            @click.stop="retry(row)"
          >
            重试
          </el-button>
          <el-button size="small" @click.stop="openJobDetail(row)">日志</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pager">
      <el-pagination
        layout="prev, pager, next, total"
        :total="total"
        :page-size="pageSize"
        :current-page="page"
        @current-change="onPageChange"
      />
    </div>

    <el-dialog v-model="showCreate" title="新建任务" width="560px">
      <el-form label-position="top">
        <el-form-item label="类型">
          <el-select v-model="jobForm.type" style="width: 100%">
            <el-option label="导入" value="import" />
            <el-option label="重建索引" value="reindex" />
            <el-option label="摘要生成" value="summary" />
          </el-select>
        </el-form-item>
        <el-form-item label="任务参数（JSON）">
          <el-input v-model="jobForm.payloadText" type="textarea" :rows="7" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="createJob">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showDetail" title="任务详情" width="760px">
      <div v-if="detailJob">
        <p><b>任务ID：</b>{{ detailJob.job_id }}</p>
        <p><b>状态：</b>{{ mapJobStatus(detailJob.status) }}（{{ detailJob.progress || 0 }}%）</p>
        <p><b>错误：</b>{{ detailJob.error || "无" }}</p>
        <p><b>参数：</b><code>{{ JSON.stringify(detailJob.payload || {}) }}</code></p>
        <el-divider />
        <div class="upload-title">任务日志</div>
        <pre class="job-log">{{ (detailJob.logs || []).join('\n') || '暂无日志' }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import {
  createAdminJob,
  getAdminJob,
  listAdminJobs,
  retryAdminJob,
  uploadImportJob
} from "../services/api";

const loading = ref(false);
const saving = ref(false);
const uploading = ref(false);
const showCreate = ref(false);
const showDetail = ref(false);
const rows = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const statusFilter = ref("");
const typeFilter = ref("");
const selectedFile = ref(null);
const detailJob = ref(null);
let timer = null;

const jobForm = reactive({
  type: "import",
  payloadText: "{\n  \"source\": \"data/anthology+abstracts1.bib\"\n}"
});

const loadJobs = async () => {
  loading.value = true;
  try {
    const data = await listAdminJobs({
      page: page.value,
      pageSize: pageSize.value,
      status: statusFilter.value,
      jobType: typeFilter.value
    });
    rows.value = data.items || [];
    total.value = data.total || 0;
  } catch (e) {
    ElMessage.error(e.detail || "加载任务失败");
  } finally {
    loading.value = false;
  }
};

const onPageChange = async (p) => {
  page.value = p;
  await loadJobs();
};

const createJob = async () => {
  let payload = {};
  try {
    payload = JSON.parse(jobForm.payloadText || "{}");
  } catch {
    ElMessage.warning("任务参数必须是合法 JSON");
    return;
  }
  saving.value = true;
  try {
    await createAdminJob({ type: jobForm.type, payload });
    ElMessage.success("任务创建成功");
    showCreate.value = false;
    await loadJobs();
  } catch (e) {
    ElMessage.error(e.detail || "创建任务失败");
  } finally {
    saving.value = false;
  }
};

const onFileChange = (event) => {
  const f = event.target?.files?.[0];
  selectedFile.value = f || null;
};

const uploadFile = async () => {
  if (!selectedFile.value) {
    ElMessage.warning("请先选择文件");
    return;
  }
  uploading.value = true;
  try {
    await uploadImportJob(selectedFile.value);
    ElMessage.success("上传成功，任务已入队");
    selectedFile.value = null;
    if (fileInput.value) fileInput.value.value = "";
    await loadJobs();
  } catch (e) {
    ElMessage.error(e.detail || "上传失败");
  } finally {
    uploading.value = false;
  }
};

const retry = async (row) => {
  try {
    await retryAdminJob(row.job_id);
    ElMessage.success("已重新入队");
    await loadJobs();
  } catch (e) {
    ElMessage.error(e.detail || "重试失败");
  }
};

const refreshOne = async () => {
  await loadJobs();
};

const openJobDetail = async (row) => {
  try {
    const data = await getAdminJob(row.job_id);
    detailJob.value = data.job;
    showDetail.value = true;
  } catch (e) {
    ElMessage.error(e.detail || "加载任务详情失败");
  }
};

const mapJobStatus = (status) => {
  const map = {
    queued: "排队中",
    running: "运行中",
    success: "成功",
    failed: "失败",
    canceled: "已取消"
  };
  return map[status] || status || "-";
};

const mapJobType = (type) => {
  const map = { import: "导入", reindex: "重建索引", summary: "摘要生成" };
  return map[type] || type || "-";
};

const fileInput = ref(null);
const startPolling = () => {
  stopPolling();
  timer = setInterval(async () => {
    const hasPending = (rows.value || []).some((r) => ["queued", "running"].includes(r.status));
    if (hasPending) await loadJobs();
  }, 3000);
};

const stopPolling = () => {
  if (timer) {
    clearInterval(timer);
    timer = null;
  }
};

onMounted(async () => {
  await loadJobs();
  startPolling();
});

onUnmounted(() => {
  stopPolling();
});
</script>
