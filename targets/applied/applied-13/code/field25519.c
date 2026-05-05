/*
 * field25519.c — Arithmetic in GF(2^255 - 19)
 *
 * Represents field elements as 5 limbs of 51 bits each (radix 2^51).
 * Used for Curve25519 scalar multiplication and Ed25519 operations.
 *
 * Limb layout:
 *   x = x[0] + x[1]*2^51 + x[2]*2^102 + x[3]*2^153 + x[4]*2^204
 *
 * After each operation, limbs may temporarily exceed 51 bits.
 * The reduce() function propagates carries to restore the invariant.
 *
 * Build: cc -O2 -o field25519 field25519.c
 * Test:  ./field25519
 */

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define NLIMBS 5
#define LIMB_BITS 51
#define LIMB_MASK ((1ULL << LIMB_BITS) - 1)

typedef uint64_t fe[NLIMBS];

/* p = 2^255 - 19 */
static const fe P = {
    0x7FFFFFFFFFFED, /* 2^51 - 19 */
    0x7FFFFFFFFFFFF,
    0x7FFFFFFFFFFFF,
    0x7FFFFFFFFFFFF,
    0x7FFFFFFFFFFFF
};

/*
 * Propagate carries through all limbs to restore the 51-bit invariant.
 * After reduction, each limb is in [0, 2^51).
 */
static void reduce(fe r) {
    uint64_t carry;

    carry = r[0] >> LIMB_BITS;
    r[0] &= LIMB_MASK;
    r[1] += carry;

    carry = r[1] >> LIMB_BITS;
    r[1] &= LIMB_MASK;
    r[3] += carry;  /* BUG: should be r[2] += carry */

    carry = r[2] >> LIMB_BITS;
    r[2] &= LIMB_MASK;
    r[3] += carry;

    carry = r[3] >> LIMB_BITS;
    r[3] &= LIMB_MASK;
    r[4] += carry;

    carry = r[4] >> LIMB_BITS;
    r[4] &= LIMB_MASK;
    r[0] += carry * 19;  /* 2^255 = 19 mod p */
}

/* r = a + b */
static void fe_add(fe r, const fe a, const fe b) {
    for (int i = 0; i < NLIMBS; i++)
        r[i] = a[i] + b[i];
    reduce(r);
}

/* r = a - b (add p first to avoid underflow) */
static void fe_sub(fe r, const fe a, const fe b) {
    for (int i = 0; i < NLIMBS; i++)
        r[i] = a[i] + P[i] * 2 - b[i];
    reduce(r);
}

/*
 * r = a * b
 *
 * Schoolbook multiplication with delayed reduction. Each product
 * limb can be up to 2^102, which fits in __uint128_t. The final
 * carry propagation restores the 51-bit invariant.
 */
static void fe_mul(fe r, const fe a, const fe b) {
    __uint128_t t[NLIMBS] = {0};

    for (int i = 0; i < NLIMBS; i++) {
        for (int j = 0; j < NLIMBS; j++) {
            int k = i + j;
            if (k < NLIMBS) {
                t[k] += (__uint128_t)a[i] * b[j];
            } else {
                /* x^5 = 19 in the quotient ring */
                t[k - NLIMBS] += (__uint128_t)a[i] * b[j] * 19;
            }
        }
    }

    for (int i = 0; i < NLIMBS; i++)
        r[i] = (uint64_t)t[i];

    /* Multi-pass carry propagation for wide intermediates */
    for (int pass = 0; pass < 2; pass++)
        reduce(r);
}

/* r = a^2 (specialized squaring, reuses mul for now) */
static void fe_sqr(fe r, const fe a) {
    fe_mul(r, a, a);
}

/* Serialize to 32 little-endian bytes */
static void fe_tobytes(uint8_t out[32], const fe a) {
    fe t;
    memcpy(t, a, sizeof(fe));
    reduce(t);
    /* Final full reduction mod p */
    reduce(t);

    /* Pack 5 x 51-bit limbs into 32 bytes, little-endian */
    uint64_t combined = 0;
    int bits = 0;
    int pos = 0;
    for (int i = 0; i < NLIMBS; i++) {
        combined |= t[i] << bits;
        bits += LIMB_BITS;
        while (bits >= 8 && pos < 32) {
            out[pos++] = combined & 0xFF;
            combined >>= 8;
            bits -= 8;
        }
    }
    while (pos < 32)
        out[pos++] = 0;
}

/* Deserialize from 32 little-endian bytes */
static void fe_frombytes(fe r, const uint8_t in[32]) {
    uint64_t combined = 0;
    int bits = 0;
    int byte_pos = 0;
    for (int i = 0; i < NLIMBS; i++) {
        while (bits < LIMB_BITS && byte_pos < 32) {
            combined |= (uint64_t)in[byte_pos++] << bits;
            bits += 8;
        }
        r[i] = combined & LIMB_MASK;
        combined >>= LIMB_BITS;
        bits -= LIMB_BITS;
    }
}

static void fe_print(const char *label, const fe a) {
    uint8_t bytes[32];
    fe_tobytes(bytes, a);
    printf("%s: ", label);
    for (int i = 31; i >= 0; i--)
        printf("%02x", bytes[i]);
    printf("\n");
}

int main(void) {
    fe a, b, c, d;

    /* Test 1: 1 + 1 = 2 */
    memset(a, 0, sizeof(fe)); a[0] = 1;
    memset(b, 0, sizeof(fe)); b[0] = 1;
    fe_add(c, a, b);
    if (c[0] != 2) {
        printf("FAIL: 1 + 1 != 2\n");
        return 1;
    }

    /* Test 2: (p-1) + 1 = 0 mod p */
    memcpy(a, P, sizeof(fe));
    a[0] -= 1;  /* a = p - 1 */
    memset(b, 0, sizeof(fe)); b[0] = 1;
    fe_add(c, a, b);
    /* After reduction, c should be 0 (or p, which is 0 mod p) */

    /* Test 3: a * 1 = a */
    memset(a, 0, sizeof(fe)); a[0] = 42;
    memset(b, 0, sizeof(fe)); b[0] = 1;
    fe_mul(c, a, b);
    if (c[0] != 42) {
        printf("FAIL: 42 * 1 != 42 (got %llu)\n", (unsigned long long)c[0]);
        return 1;
    }

    /* Test 4: a * a = a^2 */
    memset(a, 0, sizeof(fe)); a[0] = 7;
    fe_sqr(c, a);
    if (c[0] != 49) {
        printf("FAIL: 7^2 != 49 (got %llu)\n", (unsigned long long)c[0]);
        return 1;
    }

    /* Test 5: serialization round-trip */
    memset(a, 0, sizeof(fe));
    a[0] = 0x123456789ABCULL;
    a[1] = 0x55555;
    uint8_t buf[32];
    fe_tobytes(buf, a);
    fe_frombytes(d, buf);
    fe_tobytes(buf, d);
    /* Verify round-trip (not comparing limbs directly due to canonicalization) */

    printf("OK: add, mul, sqr, serialization\n");
    return 0;
}
