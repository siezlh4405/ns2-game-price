<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Game } from '../types/game'

const props = defineProps<{
  game: Game
  isWishlisted: boolean
}>()

const emit = defineEmits<{
  (e: 'toggle-wishlist', nsuid: string): void
}>()

const imgStage = ref<'proxy' | 'direct' | 'failed'>('proxy')

watch(
  () => props.game.imageUrl,
  () => {
    imgStage.value = 'proxy'
  }
)

const displayImageUrl = computed(() => {
  const raw = props.game.imageUrl
  if (!raw || imgStage.value === 'failed') return ''
  if (imgStage.value === 'proxy') {
    return `https://wsrv.nl/?url=${encodeURIComponent(raw)}&w=480&output=webp`
  }
  return raw
})

function onImageError() {
  if (imgStage.value === 'proxy') {
    imgStage.value = 'direct'
  } else {
    imgStage.value = 'failed'
  }
}

const platformBadge = computed(() => {
  switch (props.game.platform) {
    case 'switch2':
      return {
        label: 'Switch 2',
        classes: 'bg-nintendo text-white',
      }
    case 'switch2_edition':
      return {
        label: 'Switch 2 Edition',
        classes: 'bg-gradient-to-r from-nintendo to-orange-500 text-white',
      }
    default:
      return {
        label: 'Switch',
        classes: 'bg-slate-700/90 text-slate-200',
      }
  }
})

const daysLeftLabel = computed(() => {
  if (!props.game.discountEnd) return ''
  const endMs = new Date(props.game.discountEnd).getTime()
  if (Number.isNaN(endMs)) return ''
  const diffDays = Math.ceil((endMs - Date.now()) / (1000 * 60 * 60 * 24))
  if (diffDays < 0) return '特價已結束'
  if (diffDays === 0) return '今日截止'
  return `剩 ${diffDays} 天`
})

const formattedEndDate = computed(() => {
  if (!props.game.discountEnd) return ''
  const d = new Date(props.game.discountEnd)
  if (Number.isNaN(d.getTime())) return ''
  return `${d.getMonth() + 1}/${d.getDate()}`
})

function formatTwd(price: number): string {
  return `NT$ ${price.toLocaleString('zh-TW')}`
}
</script>

<template>
  <article
    class="group flex flex-col overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/90 shadow-lg transition hover:-translate-y-0.5 hover:border-slate-700 hover:shadow-xl"
  >
    <div class="relative aspect-video w-full overflow-hidden bg-slate-800">
      <a :href="game.storeUrl" target="_blank" rel="noopener noreferrer" class="block h-full w-full">
        <img
          v-if="displayImageUrl"
          :src="displayImageUrl"
          :alt="game.title"
          loading="lazy"
          referrerpolicy="no-referrer"
          class="h-full w-full object-cover transition duration-300 group-hover:scale-105"
          @error="onImageError"
        />
        <div
          v-else
          class="flex h-full w-full items-center justify-center text-sm text-slate-500"
        >
          無封面圖片
        </div>
      </a>

      <!-- Top-left badges -->
      <div class="pointer-events-none absolute left-2.5 top-2.5 flex flex-wrap gap-1.5">
        <span
          :class="platformBadge.classes"
          class="rounded-md px-2 py-0.5 text-xs font-semibold shadow"
        >
          {{ platformBadge.label }}
        </span>
        <span
          v-if="game.isAllTimeLow"
          class="rounded-md bg-amber-400 px-2 py-0.5 text-xs font-bold text-slate-950 shadow"
        >
          🔥 史低
        </span>
      </div>

      <!-- Top-right wishlist button -->
      <button
        type="button"
        :aria-label="isWishlisted ? '移出願望清單' : '加入願望清單'"
        class="absolute right-2.5 top-2.5 flex h-8 w-8 items-center justify-center rounded-full bg-slate-950/75 text-lg backdrop-blur transition hover:scale-110 hover:bg-slate-900"
        @click.stop="emit('toggle-wishlist', game.nsuid)"
      >
        <span :class="isWishlisted ? 'text-rose-500' : 'text-slate-300'">
          {{ isWishlisted ? '♥' : '♡' }}
        </span>
      </button>

      <!-- Bottom-right discount badge -->
      <span
        v-if="game.isOnSale && game.discountPercent > 0"
        class="pointer-events-none absolute bottom-2.5 right-2.5 rounded-lg bg-rose-600 px-2.5 py-1 text-sm font-extrabold text-white shadow-md"
      >
        -{{ game.discountPercent }}%
      </span>
    </div>

    <div class="flex flex-1 flex-col justify-between p-4">
      <div>
        <a
          :href="game.storeUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="line-clamp-2 text-base font-semibold leading-snug text-slate-100 transition hover:text-rose-400"
          :title="game.title"
        >
          {{ game.title }}
        </a>
        <p class="mt-1 text-xs text-slate-400">
          <span v-if="game.releaseDate">發售 {{ game.releaseDate }}</span>
          <span v-if="game.releaseDate && game.publisher"> · </span>
          <span v-if="game.publisher">{{ game.publisher }}</span>
        </p>
      </div>

      <div class="mt-4 border-t border-slate-800 pt-3">
        <div class="flex items-end justify-between gap-2">
          <div>
            <div v-if="game.isOnSale" class="flex items-baseline gap-2">
              <span class="text-xl font-bold text-rose-400">
                {{ formatTwd(game.currentPrice) }}
              </span>
              <span class="text-xs text-slate-500 line-through">
                {{ formatTwd(game.regularPrice) }}
              </span>
            </div>
            <div v-else class="text-lg font-bold text-slate-200">
              {{ formatTwd(game.regularPrice) }}
            </div>

            <p
              v-if="game.allTimeLow !== null && game.allTimeLow < game.regularPrice"
              class="mt-0.5 text-xs text-slate-400"
            >
              歷史低價 {{ formatTwd(game.allTimeLow) }}
            </p>
          </div>

          <div v-if="game.isOnSale && daysLeftLabel" class="text-right">
            <span
              class="inline-block rounded-md bg-rose-500/15 px-2 py-0.5 text-xs font-medium text-rose-300"
            >
              {{ daysLeftLabel }}
            </span>
            <p v-if="formattedEndDate" class="mt-0.5 text-[11px] text-slate-500">
              至 {{ formattedEndDate }}
            </p>
          </div>
        </div>
      </div>
    </div>
  </article>
</template>
