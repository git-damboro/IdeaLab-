<template>
  <div>
    <div class="page-head">
      <h2>审稿流程</h2>
      <div class="actions">
        <el-input v-model="keyword" placeholder="搜索论文标题/摘要" clearable @keyup.enter="loadRows" />
        <el-select v-model="workflowStatus" clearable placeholder="流程状态" style="width: 160px">
          <el-option v-for="x in workflowOptions" :key="x.code" :label="x.name" :value="x.code" />
        </el-select>
        <el-button type="primary" @click="loadRows">搜索</el-button>
      </div>
    </div>

    <el-table :data="rows" border v-loading="loading">
      <el-table-column prop="paper_id" label="论文ID" width="110" />
      <el-table-column prop="title" label="标题" min-width="340" />
      <el-table-column label="流程状态" width="140">
        <template #default="{ row }">{{ workflowName(row.workflow_status) }}</template>
      </el-table-column>
      <el-table-column label="发布状态" width="120">
        <template #default="{ row }">{{ paperStatusName(row.status) }}</template>
      </el-table-column>
      <el-table-column prop="updated_at" label="更新时间" min-width="180" />
      <el-table-column label="操作" width="220">
        <template #default="{ row }">
          <el-button size="small" @click="openRecords(row)">记录</el-button>
          <el-button size="small" type="primary" @click="openTransition(row)">流转</el-button>
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

    <el-dialog v-model="showTransition" title="推进审稿流程" width="560px">
      <div v-if="activeRow">
        <p><b>论文：</b>{{ activeRow.title }}</p>
        <p><b>当前状态：</b>{{ workflowName(activeRow.workflow_status) }}</p>
        <el-form label-position="top">
          <el-form-item label="下一状态">
            <el-select v-model="transitionForm.next_status" style="width: 100%">
              <el-option v-for="x in transitionCandidates" :key="x.code" :label="x.name" :value="x.code" />
            </el-select>
          </el-form-item>
          <el-form-item label="意见">
            <el-input v-model="transitionForm.comment" type="textarea" :rows="4" placeholder="填写审稿意见/流转说明" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="showTransition = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitTransition">确认</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showRecords" title="审稿记录" width="760px">
      <div v-if="recordPaperTitle" style="margin-bottom: 8px">
        <b>{{ recordPaperTitle }}</b>
      </div>
      <el-timeline>
        <el-timeline-item v-for="(item, idx) in records" :key="idx" :timestamp="String(item.at || '-')">
          <div>
            <b>{{ workflowName(item.from_status) }} -> {{ workflowName(item.to_status) }}</b>
          </div>
          <div>操作人：{{ item.actor || '-' }}</div>
          <div>意见：{{ item.comment || '无' }}</div>
        </el-timeline-item>
      </el-timeline>
      <div v-if="records.length === 0" class="hint">暂无审稿记录</div>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import {
  getWorkflowOptions,
  listReviewPipeline,
  listReviewRecords,
  transitionReviewWorkflow
} from "../services/api";

const loading = ref(false);
const saving = ref(false);
const rows = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const keyword = ref("");
const workflowStatus = ref("");
const workflowOptions = ref([]);
const transitions = ref({});

const showTransition = ref(false);
const showRecords = ref(false);
const activeRow = ref(null);
const records = ref([]);
const recordPaperTitle = ref("");

const transitionForm = reactive({
  next_status: "",
  comment: ""
});

const loadWorkflowMeta = async () => {
  const data = await getWorkflowOptions();
  workflowOptions.value = data.items || [];
  transitions.value = data.transitions || {};
};

const loadRows = async () => {
  loading.value = true;
  try {
    const data = await listReviewPipeline({
      page: page.value,
      pageSize: pageSize.value,
      keyword: keyword.value,
      workflowStatus: workflowStatus.value
    });
    rows.value = data.items || [];
    total.value = data.total || 0;
  } catch (e) {
    ElMessage.error(e.detail || "加载审稿流程失败");
  } finally {
    loading.value = false;
  }
};

const onPageChange = async (p) => {
  page.value = p;
  await loadRows();
};

const workflowName = (code) => {
  const found = (workflowOptions.value || []).find((x) => x.code === code);
  return found?.name || code || "-";
};

const paperStatusName = (status) => {
  const map = { draft: "草稿", published: "已发布", offline: "已下架" };
  return map[status] || status || "-";
};

const transitionCandidates = ref([]);

const openTransition = (row) => {
  activeRow.value = row;
  transitionForm.comment = "";
  const candidates = transitions.value[row.workflow_status] || [];
  transitionCandidates.value = candidates
    .map((code) => workflowOptions.value.find((x) => x.code === code))
    .filter(Boolean);
  transitionForm.next_status = transitionCandidates.value[0]?.code || "";
  if (!transitionCandidates.value.length) {
    ElMessage.warning("当前状态没有可执行的后续流转");
    return;
  }
  showTransition.value = true;
};

const submitTransition = async () => {
  if (!activeRow.value) return;
  if (!transitionForm.next_status) {
    ElMessage.warning("请选择下一状态");
    return;
  }
  saving.value = true;
  try {
    await transitionReviewWorkflow(activeRow.value.paper_id, {
      next_status: transitionForm.next_status,
      comment: transitionForm.comment
    });
    ElMessage.success("流转成功");
    showTransition.value = false;
    await loadRows();
  } catch (e) {
    ElMessage.error(e.detail || "流程流转失败");
  } finally {
    saving.value = false;
  }
};

const openRecords = async (row) => {
  try {
    const data = await listReviewRecords(row.paper_id);
    records.value = (data.records || []).slice().reverse();
    recordPaperTitle.value = data.title || "";
    showRecords.value = true;
  } catch (e) {
    ElMessage.error(e.detail || "加载审稿记录失败");
  }
};

onMounted(async () => {
  try {
    await loadWorkflowMeta();
    await loadRows();
  } catch (e) {
    ElMessage.error(e.detail || "初始化失败");
  }
});
</script>
