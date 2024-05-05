theory Example
  imports Main
begin

theorem example:
  fixes x y z :: real and p :: rat
  assumes "0 < x" "0 < y" "0 < z"
    and "x * y * z = 1"
    and "x + 1 / z = 5"
    and "y + 1 / x = 29"
    and "z + 1 / y = p"
    and "0 < p"
  shows "let (m,n) = quotient_of p in m + n = 5"
proof
  (* your proof steps go here *)
qed
