import { computed, ref, watch } from 'vue'

const STORAGE_KEY = 'ns2_tw_wishlist_v1'

function loadInitial(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.map(String) : []
  } catch {
    return []
  }
}

const wishlistIds = ref<string[]>(loadInitial())

watch(
  wishlistIds,
  (val) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(val))
    } catch {
      // Ignore storage quota / private mode errors
    }
  },
  { deep: true }
)

export function useWishlist() {
  const idSet = computed(() => new Set(wishlistIds.value))
  const count = computed(() => wishlistIds.value.length)

  function has(nsuid: string): boolean {
    return idSet.value.has(nsuid)
  }

  function toggle(nsuid: string): void {
    if (idSet.value.has(nsuid)) {
      wishlistIds.value = wishlistIds.value.filter((id) => id !== nsuid)
    } else {
      wishlistIds.value = [...wishlistIds.value, nsuid]
    }
  }

  return {
    wishlistIds,
    count,
    has,
    toggle,
  }
}
