import { describe, expect, it } from 'vitest'

import PRODUCT from '../../product.json'
import { PRODUCT_NAME } from './branding'

describe('the product name (task-29)', () => {
  it('is the one product.json holds, not one spelled out in the client', () => {
    expect(PRODUCT_NAME).toBe(PRODUCT.name)
  })
})
