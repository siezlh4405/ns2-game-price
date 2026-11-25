<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import GameCard from './components/GameCard.vue'
import { useWishlist } from './composables/useWishlist'
import type { FilterTab, Game, GamesPayload, SortOption } from './types/game'

const payload = ref<GamesPayload | null>(null)
const loading = ref(true)
const errorMessage = ref('')

const activeTab = ref<FilterTab>('on_sale')
const searchQuery = ref('')
const sortBy = ref<SortOption>('discount_desc')
const onlyOnSaleInTab = ref(false)

const { has: isWishlisted, toggle: toggleWishlist, count: wishlistCount } = useWishlist()

onMounted(async () => {
  try {
    const res = await fetch('./data/games.json', { cache: 'no-store' })
    if (!res.ok) {
      throw new Error(`無法載入遊戲資料 (HTTP ${res.status})`)
    }
    payload.value = (await res.json()) as GamesPayload
  } catch (err) {
    errorMessage.value =
      err instanceof Error ? err.message : '載入資料時發生未知錯誤'
  } finally {
    loading.value = false
  }
})

const formattedUpdatedAt = computed(() => {
  if (!payload.value?.updatedAt) return ''
  const d = new Date(payload.value.updatedAt)
  if (Number.isNaN(d.getTime())) return payload.value.updatedAt
  return new Intl.DateTimeFormat('zh-TW', {
    timeZone: 'Asia/Taipei',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(d)
})

const filteredGames = computed<Game[]>(() => {
  const games = payload.value?.games ?? []
  const q = searchQuery.value.trim().toLowerCase()

  const list = games.filter((g) => {
    if (activeTab.value === 'on_sale' && !g.isOnSale) return false
    if (
      activeTab.value === 'switch2' &&
      g.platform !== 'switch2' &&
      g.platform !== 'switch2_edition'
    ) {
      return false
    }
    if (activeTab.value === 'switch' && g.platform !== 'switch') return false
    if (activeTab.value === 'wishlist' && !isWishlisted(g.nsuid)) return false

    if (activeTab.value !== 'on_sale' && onlyOnSaleInTab.value && !g.isOnSale) {
      return false
    }

    if (q) {
      const hitTitle = g.title.toLowerCase().includes(q)
      const hitPub = g.publisher.toLowerCase().includes(q)
      const hitId = g.nsuid.includes(q)
      if (!hitTitle && !hitPub && !hitId) return false
    }
    return true
  })

  return [...list].sort((a, b) => {
    switch (sortBy.value) {
      case 'discount_desc':
        if (b.discountPercent !== a.discountPercent) {
          return b.discountPercent - a.discountPercent
        }
        return a.currentPrice - b.currentPrice
      case 'ending_soon': {
        const aEnd = a.discountEnd ? new Date(a.discountEnd).getTime() : Infinity
        const bEnd = b.discountEnd ? new Date(b.discountEnd).getTime() : Infinity
        if (aEnd !== bEnd) return aEnd - bEnd
        return b.discountPercent - a.discountPercent
      }
      case 'price_asc':
        return a.currentPrice - b.currentPrice
      case 'price_desc':
        return b.currentPrice - a.currentPrice
      case 'release_desc':
        return (b.releaseDate || '').localeCompare(a.releaseDate || '')
      default:
        return 0
    }
  })
})

const tabs = computed<{ key: FilterTab; label: string; count?: number }[]>(() => [
  { key: 'on_sale', label: '🔥 特價中', count: payload.value?.stats.onSale },
  { key: 'switch2', label: 'Switch 2', count: payload.value?.stats.switch2 },
  { key: 'wishlist', label: '♥ 願望清單', count: wishlistCount.value },
  { key: 'switch', label: 'Switch' },
  { key: 'all', label: '全部遊戲', count: payload.value?.stats.total },
])
</script>

<template>
  <div class="min-h-screen bg-slate-950 text-slate-100">
    <!-- Header -->
    <header class="border-b border-slate-800/80 bg-slate-900/70 backdrop-blur">
      <div class="mx-auto max-w-7xl px-4 py-5 sm:px-6 lg:px-8">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div class="flex items-center gap-2.5">
              <span
                class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-nintendo text-sm font-black text-white shadow"
              >
                NS2
              </span>
              <h1 class="text-xl font-bold tracking-tight text-white sm:text-2xl">
                台灣 eShop 特價追蹤
              </h1>
            </div>
            <p class="mt-1 text-xs text-slate-400 sm:text-sm">
              自動追蹤 Nintendo Switch 2 / Switch 台灣區新台幣（TWD）價格與折扣
            </p>
          </div>

          <div
            v-if="payload"
            class="flex flex-wrap items-center gap-3 text-xs text-slate-400"
          >
            <span class="rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5">
              最後更新：<strong class="text-slate-200">{{ formattedUpdatedAt }}</strong>
            </span>
          </div>
        </div>

        <!-- Tabs & Controls -->
        <div class="mt-5 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div class="flex flex-wrap gap-2">
            <button
              v-for="tab in tabs"
              :key="tab.key"
              type="button"
              :class="[
                activeTab === tab.key
                  ? 'bg-nintendo text-white shadow'
                  : 'bg-slate-800/80 text-slate-300 hover:bg-slate-800 hover:text-white',
              ]"
              class="inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-sm font-medium transition"
              @click="activeTab = tab.key"
            >
              <span>{{ tab.label }}</span>
              <span
                v-if="tab.count !== undefined"
                :class="[
                  activeTab === tab.key
                    ? 'bg-white/20 text-white'
                    : 'bg-slate-700 text-slate-300',
                ]"
                class="rounded-full px-1.5 py-0.5 text-xs font-semibold"
              >
                {{ tab.count }}
              </span>
            </button>
          </div>

          <div class="flex flex-wrap items-center gap-2.5">
            <label
              v-if="activeTab !== 'on_sale'"
              class="inline-flex cursor-pointer items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-slate-300"
            >
              <input
                v-model="onlyOnSaleInTab"
                type="checkbox"
                class="h-3.5 w-3.5 rounded accent-nintendo"
              />
              只看特價
            </label>

            <input
              v-model="searchQuery"
              type="search"
              placeholder="搜尋遊戲名稱、發行商或 NSUID..."
              class="w-full rounded-xl border border-slate-800 bg-slate-900 px-3.5 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-rose-500 focus:outline-none sm:w-64"
            />

            <select
              v-model="sortBy"
              class="rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-rose-500 focus:outline-none"
            >
              <option value="discount_desc">折扣最多</option>
              <option value="ending_soon">特價即將結束</option>
              <option value="price_asc">價格由低到高</option>
              <option value="price_desc">價格由高到低</option>
              <option value="release_desc">最新發售</option>
            </select>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <div v-if="loading" class="py-20 text-center text-slate-400">
        載入台灣 eShop 資料中...
      </div>

      <div
        v-else-if="errorMessage"
        class="rounded-2xl border border-rose-500/30 bg-rose-950/30 p-6 text-center text-rose-300"
      >
        {{ errorMessage }}
      </div>

      <template v-else>
        <div class="mb-4 flex items-center justify-between text-xs text-slate-400">
          <span>顯示 {{ filteredGames.length }} 款遊戲</span>
          <span v-if="activeTab === 'wishlist'">願望清單儲存在本機瀏覽器中</span>
        </div>

        <div
          v-if="filteredGames.length === 0"
          class="rounded-2xl border border-slate-800 bg-slate-900/60 p-12 text-center text-slate-400"
        >
          <p class="text-base font-medium text-slate-300">找不到符合條件的遊戲</p>
          <p class="mt-1 text-xs text-slate-500">
            試試看切換分類或清除搜尋關鍵字
          </p>
        </div>

        <div
          v-else
          class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
        >
          <GameCard
            v-for="game in filteredGames"
            :key="game.nsuid"
            :game="game"
            :is-wishlisted="isWishlisted(game.nsuid)"
            @toggle-wishlist="toggleWishlist"
          />
        </div>
      </template>
    </main>

    <footer class="mt-12 border-t border-slate-900 py-6 text-center text-xs text-slate-500">
      資料由 GitHub Actions 定時查詢任天堂台灣區價格 API（TWD），實際售價以主機 Nintendo eShop 為準。
    </footer>
  </div>
</template>
