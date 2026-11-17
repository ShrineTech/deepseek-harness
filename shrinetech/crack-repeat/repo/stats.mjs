// Moving average over a window of n values.
export function movingAverage(values, n) {
  const out = []
  for (let i = 0; i + n < values.length; i++) {
    let sum = 0
    for (let j = i; j < i + n; j++) sum += values[j]
    out.push(sum / n)
  }
  return out
}
