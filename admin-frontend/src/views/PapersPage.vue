<template>
  <div>
    <div class="page-head">
      <h2>论文管理</h2>
      <div class="actions">
        <el-input v-model="keyword" placeholder="按标题/摘要搜索" clearable @keyup.enter="loadPapers" />
        <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 140px">
          <el-option label="草稿" value="draft" />
          <el-option label="已发布" value="published" />
          <el-option label="已下架" value="offline" />
        </el-select>
        <el-button type="primary" @click="loadPapers">搜索</el-button>
        <el-button @click="showCreate = true">新建论文</el-button>
      </div>
    </div>

    <el-table :data="rows" v-loading="loading" border>
      <el-table-column prop="paper_id" label="ID" width="100" />
      <el-table-column prop="title" label="标题" min-width="360">
        <template #default="{ row }">
          <router-link :to="`/papers/${row.paper_id}`">{{ row.title }}</router-link>
        </template>
      </el-table-column>
      <el-table-column prop="year" label="年份" width="100" />
      <el-table-column label="状态" width="120">
        <template #default="{ row }">{{ mapPaperStatus(row.status) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="220">
        <template #default="{ row }">
          <el-button size="small" type="success" plain @click="setPublished(row)">发布</el-button>
          <el-button size="small" type="warning" plain @click="setOffline(row)">下架</el-button>
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

    <el-dialog v-model="showCreate" title="新建论文" width="640px">
      <el-form label-position="top">
        <el-form-item label="标题"><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="摘要"><el-input v-model="form.abstract" type="textarea" :rows="4" /></el-form-item>
        <el-form-item label="作者（英文逗号分隔）"><el-input v-model="form.authorsRaw" /></el-form-item>
        <el-form-item label="年份"><el-input-number v-model="form.year" :min="1900" :max="2100" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="createPaper">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { createAdminPaper, listAdminPapers, offlineAdminPaper, publishAdminPaper } from "../services/api";

const loading = ref(false);
const saving = ref(false);
const showCreate = ref(false);
const rows = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const keyword = ref("");
const statusFilter = ref("");

const form = reactive({
  title: "",
  abstract: "",
  authorsRaw: "",
  year: new Date().getFullYear()
});

const loadPapers = async () => {
  loading.value = true;
  try {
    const data = await listAdminPapers({
      page: page.value,
      pageSize: pageSize.value,
      keyword: keyword.value,
      status: statusFilter.value
    });
    rows.value = data.items || [];
    total.value = data.total || 0;
  } catch (e) {
    ElMessage.error(e.detail || "加载论文失败");
  } finally {
    loading.value = false;
  }
};

const onPageChange = async (p) => {
  page.value = p;
  await loadPapers();
};

const createPaper = async () => {
  if (!form.title.trim()) {
    ElMessage.warning("标题不能为空");
    return;
  }
  saving.value = true;
  try {
    const authors = form.authorsRaw.split(",").map((x) => x.trim()).filter(Boolean);
    await createAdminPaper({
      title: form.title,
      abstract: form.abstract,
      authors,
      year: form.year,
      status: "draft"
    });
    ElMessage.success("创建成功");
    showCreate.value = false;
    form.title = "";
    form.abstract = "";
    form.authorsRaw = "";
    form.year = new Date().getFullYear();
    await loadPapers();
  } catch (e) {
    ElMessage.error(e.detail || "创建失败");
  } finally {
    saving.value = false;
  }
};

const setPublished = async (row) => {
  try {
    await publishAdminPaper(row.paper_id);
    ElMessage.success("发布成功");
    await loadPapers();
  } catch (e) {
    ElMessage.error(e.detail || "发布失败");
  }
};

const setOffline = async (row) => {
  try {
    await offlineAdminPaper(row.paper_id);
    ElMessage.success("下架成功");
    await loadPapers();
  } catch (e) {
    ElMessage.error(e.detail || "下架失败");
  }
};

const mapPaperStatus = (status) => {
  const map = { draft: "草稿", published: "已发布", offline: "已下架" };
  return map[status] || status || "-";
};

onMounted(loadPapers);
</script>
