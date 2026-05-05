<template>
  <div>
    <div class="page-head">
      <h2>编辑论文 #{{ paperId }}</h2>
      <div class="actions">
        <el-button @click="$router.push('/papers')">返回</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </div>
    </div>

    <el-card v-loading="loading">
      <el-form label-position="top">
        <el-form-item label="标题"><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="摘要"><el-input v-model="form.abstract" type="textarea" :rows="10" /></el-form-item>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="年份"><el-input-number v-model="form.year" :min="1900" :max="2100" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="月份"><el-input v-model="form.month" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="状态">
              <el-select v-model="form.status" style="width: 100%">
                <el-option label="草稿" value="draft" />
                <el-option label="已发布" value="published" />
                <el-option label="已下架" value="offline" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="来源/会议信息"><el-input v-model="form.venue" /></el-form-item>
        <el-form-item label="作者（英文逗号分隔）"><el-input v-model="form.authorsRaw" /></el-form-item>
        <el-form-item label="关键词（英文逗号分隔）"><el-input v-model="form.keywordsRaw" /></el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { getAdminPaper, updateAdminPaper } from "../services/api";

const route = useRoute();
const paperId = Number(route.params.id);
const loading = ref(false);
const saving = ref(false);

const form = reactive({
  title: "",
  abstract: "",
  year: new Date().getFullYear(),
  month: "",
  status: "draft",
  venue: "",
  authorsRaw: "",
  keywordsRaw: ""
});

const load = async () => {
  loading.value = true;
  try {
    const data = await getAdminPaper(paperId);
    const p = data.paper;
    form.title = p.title || "";
    form.abstract = p.abstract || "";
    form.year = p.year || new Date().getFullYear();
    form.month = p.month || "";
    form.status = p.status || "draft";
    form.venue = p.venue || "";
    form.authorsRaw = (p.authors || []).join(", ");
    form.keywordsRaw = (p.keywords || []).join(", ");
  } catch (e) {
    ElMessage.error(e.detail || "加载论文失败");
  } finally {
    loading.value = false;
  }
};

const save = async () => {
  if (!form.title.trim()) {
    ElMessage.warning("标题不能为空");
    return;
  }
  saving.value = true;
  try {
    await updateAdminPaper(paperId, {
      title: form.title,
      abstract: form.abstract,
      year: form.year,
      month: form.month,
      status: form.status,
      venue: form.venue,
      authors: form.authorsRaw.split(",").map((x) => x.trim()).filter(Boolean),
      keywords: form.keywordsRaw.split(",").map((x) => x.trim()).filter(Boolean)
    });
    ElMessage.success("保存成功");
  } catch (e) {
    ElMessage.error(e.detail || "保存失败");
  } finally {
    saving.value = false;
  }
};

onMounted(load);
</script>
