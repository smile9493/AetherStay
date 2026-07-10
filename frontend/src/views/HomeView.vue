<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/api'
import {
  isOnOrBeforeDateStr,
  isPastDate,
  isValidDateRange,
} from '@/utils/dates'
import {
  Search,
  Location,
  Coffee,
  Service,
  Van,
  Sunny,
} from '@element-plus/icons-vue'

interface Room {
  id: number
  room_number: string
  room_type_id: number
  status: string
  room_type: {
    id: number
    name: string
    base_price: string
    capacity: number
    total_rooms?: number
    description?: string
    amenities?: string
    image_url?: string
  }
}

interface RoomTypeCard {
  id: number
  name: string
  base_price: string
  capacity: number
  total_rooms: number
  description?: string
  amenities?: string
  image_url?: string
}

const router = useRouter()
const loading = ref(false)

const searchForm = ref({
  check_in: '',
  check_out: '',
})

const roomTypes = ref<RoomTypeCard[]>([])

const amenities = [
  { icon: Sunny, title: '舒适客房', desc: '精心布置的客房，营造温馨入住体验' },
  { icon: Coffee, title: '自助早餐', desc: '每日新鲜早餐，开启美好一天' },
  { icon: Service, title: '24 小时前台', desc: '全天候贴心服务，随时响应您的需求' },
  { icon: Van, title: '行李寄存', desc: '免费行李寄存，出行更加轻松' },
]

onMounted(loadRoomTypes)

async function loadRoomTypes() {
  loading.value = true
  try {
    const { data } = await api.get<Room[]>('/rooms')
    const map = new Map<number, RoomTypeCard>()
    for (const room of data) {
      if (!room.room_type || room.status !== 'active') continue
      const rt = room.room_type
      if (map.has(rt.id)) continue
      map.set(rt.id, {
        id: rt.id,
        name: rt.name,
        base_price: rt.base_price,
        capacity: rt.capacity,
        total_rooms: rt.total_rooms ?? 0,
        description: rt.description,
        amenities: rt.amenities,
        image_url: rt.image_url,
      })
    }
    roomTypes.value = Array.from(map.values())
  } catch {
    ElMessage.error('加载房型信息失败')
  } finally {
    loading.value = false
  }
}

watch(
  () => searchForm.value.check_in,
  (checkIn) => {
    const checkOut = searchForm.value.check_out
    if (checkIn && checkOut && !isValidDateRange(checkIn, checkOut)) {
      searchForm.value.check_out = ''
    }
  },
)

function searchRooms() {
  if (!searchForm.value.check_in || !searchForm.value.check_out) {
    ElMessage.warning('请选择入住和退房日期')
    return
  }
  if (!isValidDateRange(searchForm.value.check_in, searchForm.value.check_out)) {
    ElMessage.warning('退房日期必须晚于入住日期')
    return
  }
  router.push({
    path: '/rooms',
    query: {
      check_in: searchForm.value.check_in,
      check_out: searchForm.value.check_out,
    },
  })
}

function goToRooms(typeId?: number) {
  const query: Record<string, string> = {}
  if (searchForm.value.check_in) query.check_in = searchForm.value.check_in
  if (searchForm.value.check_out) query.check_out = searchForm.value.check_out
  if (typeId) query.room_type_id = String(typeId)
  router.push({ path: '/rooms', query })
}
</script>

<template>
  <div class="home-page">
    <!-- Hero + 预订搜索 -->
    <section class="hero">
      <div class="hero-bg" />
      <div class="hero-overlay" />
      <div class="hero-inner">
        <div class="hero-text">
          <p class="hero-tag">城市中心 · 品质之选</p>
          <h1 class="hero-title">AetherStay 酒店</h1>
          <p class="hero-desc">
            毗邻商圈与交通枢纽，为您提供安静舒适的休憩空间。在线预订，完成支付后订单即时确认。
          </p>
          <p class="hero-location">
            <el-icon><Location /></el-icon>
            市中心商业区 · 步行 5 分钟可达地铁站
          </p>
        </div>

        <div class="search-card glass-panel">
          <h3 class="search-title">查询空房与最优价格</h3>
          <el-form :inline="true" class="search-form" @submit.prevent="searchRooms">
            <el-form-item label="入住">
              <el-date-picker
                v-model="searchForm.check_in"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="选择日期"
                :disabled-date="isPastDate"
              />
            </el-form-item>
            <el-form-item label="退房">
              <el-date-picker
                v-model="searchForm.check_out"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="选择日期"
                :disabled-date="(d: Date) => searchForm.check_in ? isOnOrBeforeDateStr(d, searchForm.check_in) : isPastDate(d)"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" size="large" @click="searchRooms">
                <el-icon><Search /></el-icon>
                搜索客房
              </el-button>
            </el-form-item>
          </el-form>
        </div>
      </div>
    </section>

    <!-- 热门房型 -->
    <section class="section">
      <div class="section-header">
        <h2>热门房型</h2>
        <p>精选舒适客房，满足不同出行需求</p>
      </div>

      <el-row v-loading="loading" :gutter="24">
        <el-col
          v-for="type in roomTypes"
          :key="type.id"
          :xs="24"
          :sm="12"
          :md="8"
        >
          <div class="room-card glass-panel">
            <div
              class="room-card-img"
              :style="type.image_url
                ? { backgroundImage: `url(${type.image_url})` }
                : {}"
              :class="type.image_url ? '' : `room-type-${type.id % 3}`"
            >
              <span class="room-badge">共 {{ type.total_rooms }} 间</span>
            </div>
            <div class="room-card-body">
              <h3>{{ type.name }}</h3>
              <p class="room-meta">最多入住 {{ type.capacity }} 人</p>
              <p v-if="type.description" class="room-desc">{{ type.description }}</p>
              <div v-if="type.amenities" class="amenities-tags">
                <el-tag
                  v-for="tag in type.amenities.split(',')"
                  :key="tag"
                  size="small"
                  class="amenity-tag"
                >
                  {{ tag.trim() }}
                </el-tag>
              </div>
              <div class="room-footer">
                <div class="room-price">
                  <span class="price-label">每晚起</span>
                  <span class="price-value">¥{{ type.base_price }}</span>
                </div>
                <el-button type="primary" plain @click="goToRooms(type.id)">
                  查看详情
                </el-button>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>

      <div v-if="!loading && roomTypes.length === 0" class="empty-tip">
        暂无房型信息，请稍后再试
      </div>
    </section>

    <!-- 酒店设施 -->
    <section class="section amenities-section">
      <div class="section-header">
        <h2>酒店设施与服务</h2>
        <p>贴心设施，让您的旅途更加惬意</p>
      </div>
      <el-row :gutter="24">
        <el-col v-for="item in amenities" :key="item.title" :xs="12" :sm="6">
          <div class="amenity-card">
            <el-icon class="amenity-icon" :size="28"><component :is="item.icon" /></el-icon>
            <h4>{{ item.title }}</h4>
            <p>{{ item.desc }}</p>
          </div>
        </el-col>
      </el-row>
    </section>

    <!-- 简介 -->
    <section class="section about-section glass-panel">
      <div class="about-content">
        <h2>关于 AetherStay</h2>
        <p>
          AetherStay 酒店坐落于城市核心地段，拥有多种房型可供选择，无论是商务出差还是休闲度假，
          都能为您提供整洁、安静、便捷的住宿体验。官网预订享受会员专属价格，订单状态实时可查。
        </p>
        <el-button type="primary" size="large" @click="router.push('/rooms')">
          立即预订
        </el-button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.home-page {
  margin: -24px;
  padding-bottom: 48px;
}

/* Hero */
.hero {
  position: relative;
  min-height: 520px;
  display: flex;
  align-items: flex-end;
  padding: 0 24px 48px;
  margin-bottom: 48px;
}

.hero-bg {
  position: absolute;
  inset: 0;
  background: url('https://images.unsplash.com/photo-1566073771259-6a8506099945?w=1600&q=80') center/cover no-repeat;
}

.hero-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to top,
    rgba(15, 23, 42, 0.85) 0%,
    rgba(15, 23, 42, 0.4) 50%,
    rgba(15, 23, 42, 0.25) 100%
  );
}

.hero-inner {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 1280px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 40px;
  align-items: flex-end;
}

@media (max-width: 992px) {
  .hero-inner {
    grid-template-columns: 1fr;
    gap: 24px;
  }
}

.hero-text {
  color: #fff;
}

.hero-tag {
  font-size: 13px;
  letter-spacing: 2px;
  text-transform: uppercase;
  opacity: 0.85;
  margin-bottom: 12px;
}

.hero-title {
  font-family: var(--font-title);
  font-size: 48px;
  font-weight: 700;
  line-height: 1.15;
  margin-bottom: 16px;
}

.hero-desc {
  font-size: 16px;
  line-height: 1.7;
  opacity: 0.9;
  margin-bottom: 16px;
  max-width: 480px;
}

.hero-location {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  opacity: 0.8;
}

.search-card {
  padding: 28px 32px;
  background: rgba(255, 255, 255, 0.95) !important;
}

.search-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 20px;
  color: var(--text-primary);
}

.search-form {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.search-form :deep(.el-form-item) {
  margin-bottom: 0;
  margin-right: 12px;
}

/* Sections */
.section {
  max-width: 1280px;
  margin: 0 auto 56px;
  padding: 0 24px;
}

.section-header {
  text-align: center;
  margin-bottom: 36px;
}

.section-header h2 {
  font-family: var(--font-title);
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 8px;
}

.section-header p {
  color: var(--text-secondary);
  font-size: 15px;
}

/* Room cards */
.room-card {
  overflow: hidden;
  margin-bottom: 24px;
  transition: transform 0.25s, box-shadow 0.25s;
}

.room-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--card-shadow-hover);
}

.room-card-img {
  height: 180px;
  position: relative;
  background-size: cover;
  background-position: center;
}

.room-type-0 {
  background-image: url('https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=800&q=80');
}

.room-type-1 {
  background-image: url('https://images.unsplash.com/photo-1611892440504-42a792e56d4b?w=800&q=80');
}

.room-type-2 {
  background-image: url('https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=800&q=80');
}

.room-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 20px;
}

.room-card-body {
  padding: 20px;
}

.room-card-body h3 {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 6px;
}

.room-meta {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.room-desc {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: 10px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.amenities-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 12px;
}

.amenity-tag {
  font-size: 11px;
}

.room-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.price-label {
  display: block;
  font-size: 12px;
  color: var(--text-muted);
}

.price-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--primary-color);
}

.empty-tip {
  text-align: center;
  color: var(--text-muted);
  padding: 40px;
}

/* Amenities */
.amenities-section {
  background: rgba(255, 255, 255, 0.5);
  padding-top: 48px;
  padding-bottom: 48px;
  max-width: none;
}

.amenity-card {
  text-align: center;
  padding: 24px 16px;
}

.amenity-icon {
  color: var(--primary-color);
  margin-bottom: 12px;
}

.amenity-card h4 {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 8px;
}

.amenity-card p {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

/* About */
.about-section {
  max-width: 800px;
  margin: 0 auto;
  padding: 48px 40px;
  text-align: center;
}

.about-content h2 {
  font-family: var(--font-title);
  font-size: 24px;
  margin-bottom: 16px;
}

.about-content p {
  color: var(--text-secondary);
  line-height: 1.8;
  margin-bottom: 24px;
}
</style>
