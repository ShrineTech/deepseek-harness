import { test } from 'node:test'
import assert from 'node:assert/strict'
import { movingAverage } from './stats.mjs'

test('window of 2', () => assert.deepEqual(movingAverage([1, 2, 3, 4], 2), [1.5, 2.5, 3.5]))
test('window equals length', () => assert.deepEqual(movingAverage([2, 4], 2), [3]))
