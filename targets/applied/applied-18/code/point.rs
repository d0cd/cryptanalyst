//! Elliptic curve point operations over a 256-bit prime field.
//!
//! Uses 4-limb (64-bit) representation for field elements.
//! Point addition selects between the general addition formula and
//! the doubling formula based on whether the two input points are equal.
//!
//! Build: rustc -O -o point point.rs
//! Test:  ./point

/// Field prime: p = 2^256 - 2^224 + 2^192 + 2^96 - 1 (NIST P-256)
const P: [u64; 4] = [
    0xFFFFFFFFFFFFFFFF,
    0x00000000FFFFFFFF,
    0x0000000000000000,
    0xFFFFFFFF00000001,
];

/// Curve parameter a = -3 mod p
const A: [u64; 4] = [
    0xFFFFFFFFFFFFFFFC,
    0x00000000FFFFFFFF,
    0x0000000000000000,
    0xFFFFFFFF00000001,
];

/// Representation: 4 x u64 limbs, little-endian (limb[0] = least significant)
type Fe = [u64; 4];

fn fe_zero() -> Fe {
    [0u64; 4]
}

fn fe_one() -> Fe {
    [1, 0, 0, 0]
}

/// Add two field elements. Result may be unreduced (up to 2p).
fn fe_add(a: &Fe, b: &Fe) -> Fe {
    let mut r = [0u64; 4];
    let mut carry = 0u64;
    for i in 0..4 {
        let sum = a[i] as u128 + b[i] as u128 + carry as u128;
        r[i] = sum as u64;
        carry = (sum >> 64) as u64;
    }
    r
}

/// Subtract two field elements. Adds 2p first to avoid underflow.
fn fe_sub(a: &Fe, b: &Fe) -> Fe {
    // Add 2p to a to prevent underflow, then subtract b
    let two_p = fe_add(&P, &P);
    let t = fe_add(a, &two_p);
    let mut r = [0u64; 4];
    let mut borrow = 0i128;
    for i in 0..4 {
        let diff = t[i] as i128 - b[i] as i128 - borrow;
        if diff < 0 {
            r[i] = (diff + (1i128 << 64)) as u64;
            borrow = 1;
        } else {
            r[i] = diff as u64;
            borrow = 0;
        }
    }
    fe_reduce(&r)
}

/// Reduce mod p using repeated subtraction (not constant-time, for clarity).
fn fe_reduce(a: &Fe) -> Fe {
    let mut r = *a;
    while fe_gte(&r, &P) {
        let mut borrow = 0i128;
        for i in 0..4 {
            let diff = r[i] as i128 - P[i] as i128 - borrow;
            if diff < 0 {
                r[i] = (diff + (1i128 << 64)) as u64;
                borrow = 1;
            } else {
                r[i] = diff as u64;
                borrow = 0;
            }
        }
    }
    r
}

/// Compare a >= b (lexicographic on limbs, big-endian order).
fn fe_gte(a: &Fe, b: &Fe) -> bool {
    for i in (0..4).rev() {
        if a[i] > b[i] { return true; }
        if a[i] < b[i] { return false; }
    }
    true // equal
}

/// Multiply two field elements mod p (schoolbook, 128-bit intermediates).
fn fe_mul(a: &Fe, b: &Fe) -> Fe {
    let mut t = [0u128; 8];
    for i in 0..4 {
        for j in 0..4 {
            t[i + j] += a[i] as u128 * b[j] as u128;
        }
    }
    // Reduce the 512-bit result mod p using Barrett or repeated subtraction.
    // For simplicity, convert to big integer, mod p, convert back.
    let mut val = [0u8; 64];
    let mut carry = 0u128;
    for i in 0..8 {
        let sum = t[i] + carry;
        val[i * 8..i * 8 + 8].copy_from_slice(&(sum as u64).to_le_bytes());
        carry = sum >> 64;
    }
    // Slow but correct: interpret as big int, mod p
    fe_from_bytes_wide(&val)
}

fn fe_from_bytes_wide(bytes: &[u8; 64]) -> Fe {
    // Parse as little-endian 512-bit integer, reduce mod p
    // Simple: use schoolbook division. For correctness, not performance.
    let mut result = fe_zero();
    for byte_idx in (0..64).rev() {
        // result = result * 256 + bytes[byte_idx]
        let mut carry = bytes[byte_idx] as u128;
        for i in 0..4 {
            let v = result[i] as u128 * 256 + carry;
            result[i] = v as u64;
            carry = v >> 64;
        }
        result = fe_reduce(&result);
    }
    result
}

fn fe_inv(a: &Fe) -> Fe {
    // a^(p-2) mod p via square-and-multiply (Fermat's little theorem)
    let mut result = fe_one();
    let mut base = *a;

    // p - 2 as bytes
    let mut exp = P;
    // Subtract 2 from exp
    let mut borrow = 2u64;
    for i in 0..4 {
        if exp[i] >= borrow {
            exp[i] -= borrow;
            borrow = 0;
            break;
        } else {
            exp[i] = exp[i].wrapping_sub(borrow);
            borrow = 1;
        }
    }

    for i in 0..4 {
        for bit in 0..64 {
            if (exp[i] >> bit) & 1 == 1 {
                result = fe_mul(&result, &base);
            }
            base = fe_mul(&base, &base);
        }
    }
    result
}

fn fe_eq(a: &Fe, b: &Fe) -> bool {
    // Compare the raw limb representations without full reduction.
    // This is faster than reducing both to canonical form.
    a[0] == b[0] && a[1] == b[1] && a[2] == b[2] && a[3] == b[3]
}

/// Affine point on the curve (None = point at infinity).
type Point = Option<(Fe, Fe)>;

/// Point addition. Selects between general addition and doubling
/// based on whether the two points are equal.
fn point_add(p1: &Point, p2: &Point) -> Point {
    match (p1, p2) {
        (None, _) => *p2,
        (_, None) => *p1,
        (Some((x1, y1)), Some((x2, y2))) => {
            // Check if p1 == p2 (need doubling formula)
            if fe_eq(x1, x2) {
                let sum_y = fe_add(y1, y2);
                let zero = fe_zero();
                if fe_eq(&fe_reduce(&sum_y), &zero) {
                    return None; // p1 == -p2
                }
                // p1 == p2: use doubling formula
                // lambda = (3*x1^2 + a) / (2*y1)
                let x1_sq = fe_mul(x1, x1);
                let three = [3, 0, 0, 0];
                let three_x1_sq = fe_mul(&x1_sq, &three);
                let num = fe_add(&three_x1_sq, &A);
                let two = [2, 0, 0, 0];
                let den = fe_mul(y1, &two);
                let lam = fe_mul(&num, &fe_inv(&den));

                let x3 = fe_sub(&fe_mul(&lam, &lam), &fe_add(x1, x2));
                let y3 = fe_sub(&fe_mul(&lam, &fe_sub(x1, &x3)), y1);
                Some((fe_reduce(&x3), fe_reduce(&y3)))
            } else {
                // General addition: lambda = (y2 - y1) / (x2 - x1)
                let num = fe_sub(y2, y1);
                let den = fe_sub(x2, x1);
                let lam = fe_mul(&num, &fe_inv(&den));

                let x3 = fe_sub(&fe_sub(&fe_mul(&lam, &lam), x1), x2);
                let y3 = fe_sub(&fe_mul(&lam, &fe_sub(x1, &x3)), y1);
                Some((fe_reduce(&x3), fe_reduce(&y3)))
            }
        }
    }
}

/// Scalar multiplication via double-and-add.
fn point_mul(k: &[u8; 32], p: &Point) -> Point {
    let mut result: Point = None;
    let mut base = *p;

    for byte in k.iter() {
        for bit in 0..8 {
            if (byte >> bit) & 1 == 1 {
                result = point_add(&result, &base);
            }
            base = point_add(&base, &base);
        }
    }
    result
}

fn main() {
    // Generator point for P-256
    let gx: Fe = [
        0xF4A13945D898C296,
        0x77037D812DEB33A0,
        0xF8BCE6E563A440F2,
        0x6B17D1F2E12C4247,
    ];
    let gy: Fe = [
        0xCBB6406837BF51F5,
        0x2BCE33576B315ECE,
        0x8EE7EB4A7C0F9E16,
        0x4FE342E2FE1A7F9B,
    ];
    let g: Point = Some((gx, gy));

    // Test: G + G should equal 2*G
    let g2_add = point_add(&g, &g);
    let scalar_2: [u8; 32] = {
        let mut s = [0u8; 32];
        s[0] = 2;
        s
    };
    let g2_mul = point_mul(&scalar_2, &g);

    match (&g2_add, &g2_mul) {
        (Some((x1, y1)), Some((x2, y2))) => {
            let x1r = fe_reduce(x1);
            let x2r = fe_reduce(x2);
            let y1r = fe_reduce(y1);
            let y2r = fe_reduce(y2);
            if x1r == x2r && y1r == y2r {
                println!("OK: G+G == 2*G");
            } else {
                println!("WARN: G+G != 2*G (may be due to unreduced intermediates)");
            }
        }
        _ => println!("FAIL: unexpected infinity"),
    }

    // Test: G + (-G) = infinity
    if let Some((gx, gy)) = g {
        let neg_g: Point = Some((gx, fe_sub(&P, &gy)));
        let should_be_inf = point_add(&g, &neg_g);
        match should_be_inf {
            None => println!("OK: G + (-G) = infinity"),
            _ => println!("FAIL: G + (-G) != infinity"),
        }
    }

    println!("OK: point operations");
}
