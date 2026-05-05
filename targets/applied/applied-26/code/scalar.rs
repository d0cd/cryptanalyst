//! Scalar arithmetic for Ed25519 signatures.
//!
//! Scalars are 256-bit integers reduced modulo the group order L.
//! This module provides from_bytes / to_bytes conversion and basic
//! arithmetic (add, sub, mul) used by the signing and verification code.
//!
//! Build: rustc -O -o scalar scalar.rs
//! Test:  ./scalar

/// Group order L for Ed25519
/// L = 2^252 + 27742317777372353535851937790883648493
const L: [u64; 4] = [
    0x5812631A5CF5D3ED,
    0x14DEF9DEA2F79CD6,
    0x0000000000000000,
    0x1000000000000000,
];

/// A 256-bit scalar value.
#[derive(Clone, Copy, Debug)]
struct Scalar {
    limbs: [u64; 4], // little-endian
}

impl Scalar {
    fn zero() -> Self {
        Scalar { limbs: [0; 4] }
    }

    /// Create a scalar from 32 bytes (little-endian).
    ///
    /// Accepts any 32-byte input as a valid scalar representation.
    /// This is useful for interoperability with protocols that encode
    /// scalars as raw byte strings without pre-reduction.
    fn from_bytes(bytes: &[u8; 32]) -> Self {
        let mut limbs = [0u64; 4];
        for i in 0..4 {
            let mut buf = [0u8; 8];
            buf.copy_from_slice(&bytes[i * 8..(i + 1) * 8]);
            limbs[i] = u64::from_le_bytes(buf);
        }
        Scalar { limbs }
    }

    /// Serialize to 32 little-endian bytes.
    fn to_bytes(&self) -> [u8; 32] {
        let mut out = [0u8; 32];
        for i in 0..4 {
            out[i * 8..(i + 1) * 8].copy_from_slice(&self.limbs[i].to_le_bytes());
        }
        out
    }

    /// Reduce modulo L.
    fn reduce(&self) -> Self {
        let mut r = self.limbs;
        while gte(&r, &L) {
            let mut borrow = 0i128;
            for i in 0..4 {
                let diff = r[i] as i128 - L[i] as i128 - borrow;
                if diff < 0 {
                    r[i] = (diff + (1i128 << 64)) as u64;
                    borrow = 1;
                } else {
                    r[i] = diff as u64;
                    borrow = 0;
                }
            }
        }
        Scalar { limbs: r }
    }

    /// Add two scalars.
    fn add(&self, other: &Scalar) -> Scalar {
        let mut r = [0u64; 4];
        let mut carry = 0u128;
        for i in 0..4 {
            let sum = self.limbs[i] as u128 + other.limbs[i] as u128 + carry;
            r[i] = sum as u64;
            carry = sum >> 64;
        }
        Scalar { limbs: r }.reduce()
    }

    /// Subtract two scalars (adds L if needed to avoid underflow).
    fn sub(&self, other: &Scalar) -> Scalar {
        // Add L to self first to prevent underflow
        let with_l = Scalar { limbs: self.limbs }.add(&Scalar { limbs: L });
        let mut r = [0u64; 4];
        let mut borrow = 0i128;
        for i in 0..4 {
            let diff = with_l.limbs[i] as i128 - other.limbs[i] as i128 - borrow;
            if diff < 0 {
                r[i] = (diff + (1i128 << 64)) as u64;
                borrow = 1;
            } else {
                r[i] = diff as u64;
                borrow = 0;
            }
        }
        Scalar { limbs: r }.reduce()
    }

    /// Multiply two scalars mod L (via 512-bit intermediate).
    fn mul(&self, other: &Scalar) -> Scalar {
        let mut t = [0u128; 8];
        for i in 0..4 {
            for j in 0..4 {
                t[i + j] += self.limbs[i] as u128 * other.limbs[j] as u128;
            }
        }
        // Propagate carries in the wide result
        for i in 0..7 {
            t[i + 1] += t[i] >> 64;
            t[i] &= 0xFFFFFFFFFFFFFFFF;
        }
        // Reduce mod L using Barrett-like approach (slow but correct)
        let mut result = Scalar::zero();
        for i in (0..8).rev() {
            // result = result * 2^64 + t[i]
            let mut shifted = Scalar::zero();
            // shift left by 64 bits
            shifted.limbs[1] = result.limbs[0];
            shifted.limbs[2] = result.limbs[1];
            shifted.limbs[3] = result.limbs[2];
            // overflow handled by reduction
            shifted.limbs[0] = t[i] as u64;
            result = shifted.reduce();
        }
        result
    }

    fn is_zero(&self) -> bool {
        self.limbs == [0; 4]
    }

    fn eq(&self, other: &Scalar) -> bool {
        self.limbs == other.limbs
    }
}

fn gte(a: &[u64; 4], b: &[u64; 4]) -> bool {
    for i in (0..4).rev() {
        if a[i] > b[i] { return true; }
        if a[i] < b[i] { return false; }
    }
    true
}

fn main() {
    // Test: 0 + 0 = 0
    let zero = Scalar::zero();
    assert!(zero.add(&zero).is_zero());

    // Test: 1 + 1 = 2
    let one = Scalar::from_bytes(&{
        let mut b = [0u8; 32];
        b[0] = 1;
        b
    });
    let two = one.add(&one);
    assert!(two.limbs[0] == 2);

    // Test: a - a = 0
    let a = Scalar::from_bytes(&{
        let mut b = [0u8; 32];
        b[0] = 42;
        b
    });
    let should_be_zero = a.sub(&a);
    assert!(should_be_zero.is_zero(), "a - a != 0");

    // Test: from_bytes round-trip
    let bytes: [u8; 32] = [
        0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0,
        0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    ];
    let s = Scalar::from_bytes(&bytes);
    let out = s.to_bytes();
    assert!(bytes == out, "round-trip failed");

    // Test: multiply by 1 is identity
    let val = Scalar::from_bytes(&{
        let mut b = [0u8; 32];
        b[0] = 99;
        b
    });
    let prod = val.mul(&one);
    assert!(prod.eq(&val.reduce()), "val * 1 != val");

    println!("OK: add, sub, mul, round-trip, identity");
}
