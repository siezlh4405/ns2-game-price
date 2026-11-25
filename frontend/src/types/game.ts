export type PlatformType = 'switch2' | 'switch2_edition' | 'switch'

export interface Game {
  nsuid: string
  title: string
  platform: PlatformType
  publisher: string
  releaseDate: string
  imageUrl: string
  storeUrl: string
  salesStatus: string
  currency: string
  regularPrice: number
  discountPrice: number | null
  currentPrice: number
  discountPercent: number
  discountStart: string | null
  discountEnd: string | null
  isOnSale: boolean
  allTimeLow: number | null
  isAllTimeLow: boolean
  sources: string[]
}

export interface GamesPayload {
  updatedAt: string
  country: string
  currency: string
  stats: {
    total: number
    onSale: number
    switch2: number
    allTimeLow: number
  }
  games: Game[]
}

export type FilterTab = 'on_sale' | 'switch2' | 'switch' | 'wishlist' | 'all'

export type SortOption =
  | 'discount_desc'
  | 'ending_soon'
  | 'price_asc'
  | 'price_desc'
  | 'release_desc'
