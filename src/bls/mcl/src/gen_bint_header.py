import sys
import argparse

def gen_func(name, ret, args, cname, params, i, asPointer=False):
  retstr = '' if ret == 'void' else ' return'
  if asPointer:
    print('#if MCL_BINT_ASM_X64 == 1')
    print(f'extern "C" MCL_DLL_API {protoType[(ret,args)]} {cname}{i};')
    print(f'extern "C" {ret} {cname}_slow{i}({args});')
    print(f'extern "C" {ret} {cname}_fast{i}({args});')
    print('#else')
    print(f'extern "C" MCL_DLL_API {ret} {cname}{i}({args});')
    print('#endif')
  else:
    print(f'extern "C" MCL_DLL_API {ret} {cname}{i}({args});')
  print(f'template<> inline {ret} {name}<{i}>({args}) {{{retstr} {cname}{i}({params}); }}')

def gen_switch(name, ret, args, params, N, N64, useFuncPtr=False):
  print(f'''inline {protoType[(ret,args)]} get_{name}(size_t n)
{{
#if MCL_BINT_ASM == 1''')
  for i in range(1, N):
    if i == N64 + 1:
      print('#if MCL_SIZEOF_UNIT == 4')
    print(f'\tif (n == {i}) return mclb_{name}{i};')
  print('#endif // MCL_SIZEOF_UNIT == 4')
  print('#else // MCL_BITN_ASM == 1')
  for i in range(1, N):
    if i == N64 + 1:
      print('#if MCL_SIZEOF_UNIT == 4')
    print(f'\tif (n == {i}) return {name}T<{i}>;')
  print('''#endif // MCL_SIZEOF_UNIT == 4
#endif // MCL_BINT_ASM == 1
	CYBOZU_ASSUME(false);
}''')
  print(f'''inline {ret} {name}N({args}, size_t n)
{{
	return get_{name}(n)({params});
}}''')

def gen_inst(name, ret, args, N, N64):
  for i in range(1, N):
    if i == N64 + 1:
      print('#if MCL_SIZEOF_UNIT == 4')
    print(f'template {ret} {name}<{i}>({args});')
  print('#endif')

arg_p3 = 'Unit *z, const Unit *x, const Unit *y'
arg_p2 = 'Unit *y, const Unit *x'
arg_p2u = 'Unit *z, const Unit *x, Unit y'
param_u3 = 'z, x, y'
param_u2 = 'y, x'

protoType = {
  ('Unit', arg_p3) : 'u_ppp',
  ('void', arg_p3) : 'void_ppp',
  ('void', arg_p2) : 'void_pp',
  ('Unit', arg_p2u) : 'u_ppu',
}

def roundup(x, n):
  return (x + n - 1) // n

def gen_disable(N):
  name1 = 'mulUnit'
  name2 = 'mulUnitAdd'
  print('#if MCL_BINT_ASM_X64 == 1')
  for i in range(1, N+1):
    print(f'u_ppu mclb_{name1}{i} = mclb_{name1}_fast{i};')
    print(f'u_ppu mclb_{name2}{i} = mclb_{name2}_fast{i};')
    print(f'void_ppp mclb_mul{i} = mclb_mul_fast{i};')
    print(f'void_pp mclb_sqr{i} = mclb_sqr_fast{i};')
  print('extern "C" MCL_DLL_API void mclb_disable_fast() {')
  for i in range(1, N+1):
    print(f'\tmclb_{name1}{i} = mclb_{name1}_slow{i};')
    print(f'\tmclb_{name2}{i} = mclb_{name2}_slow{i};')
    print(f'\tmclb_mul{i} = mclb_mul_slow{i};')
    print(f'\tmclb_sqr{i} = mclb_sqr_slow{i};')
  print('}')
  print('#endif // MCL_BINT_ASM_X64 == 1')

def gen_mul_slow(N):
  print('#if MCL_BINT_ASM_X64 == 1')
  for n in range(1,N+1):
    print(f'''extern "C" void mclb_mul_slow{n}(Unit *z, const Unit *x, const Unit *y)
{{
	z[{n}] = mulUnitT<{n}>(z, x, y[0]);
	for (size_t i = 1; i < {n}; i++) {{
		z[{n} + i] = mulUnitAddT<{n}>(&z[i], x, y[i]);
	}}
}}''')
#  for n in range(1,N+1):
#    print(f'''extern "C" void mclb_mulLow_slow{n}(Unit *z, const Unit *x, const Unit *y)
#{{
#  mulUnitT<{n}>(z, x, y[0]);
#  impl::UnrollMulLowT<{n}>::call(z, x, y);
#}}''')
  print('#endif // MCL_BINT_ASM_X64 == 1')

def gen_sqr_slow(N):
  print('#if MCL_BINT_ASM_X64 == 1')
  for n in range(1,N+1):
    print(f'''extern "C" void mclb_sqr_slow{n}(Unit *y, const Unit *x)
{{
	mclb_mul_slow{n}(y, x, x);
}}''')
  print('#endif // MCL_BINT_ASM_X64 == 1')

def main():
  parser = argparse.ArgumentParser(description='gen header')
  parser.add_argument('out', type=str)
  parser.add_argument('-max_bit', type=int, default=512+32)
  opt = parser.parse_args()
  if not opt.out in ['proto', 'switch']:
    print('bad out', opt.out)
    sys.exit(1)
  N = roundup(opt.max_bit, 32)
  N64 = roundup(opt.max_bit, 64)
  addN = 32
  addN64 = 16

  print('// this code is generated by python3 src/gen_bint_header.py', opt.out)
  if opt.out == 'proto':
    print('#if MCL_BINT_ASM == 1')
    for i in range(1, addN+1):
      if i == addN64 + 1:
        print('#if MCL_SIZEOF_UNIT == 4')
      gen_func('addT', 'Unit', arg_p3, 'mclb_add', param_u3, i)
      gen_func('subT', 'Unit', arg_p3, 'mclb_sub', param_u3, i)
      gen_func('addNFT', 'void', arg_p3, 'mclb_addNF', param_u3, i)
      gen_func('subNFT', 'Unit', arg_p3, 'mclb_subNF', param_u3, i)
    print('#endif // #if MCL_SIZEOF_UNIT == 4')
    for i in range(1, N+1):
      if i == N64 + 1:
        print('#if MCL_SIZEOF_UNIT == 4')
      gen_func('mulUnitT', 'Unit', arg_p2u, 'mclb_mulUnit', param_u3, i, True)
      gen_func('mulUnitAddT', 'Unit', arg_p2u, 'mclb_mulUnitAdd', param_u3, i, True)
      gen_func('mulT', 'void', arg_p3, 'mclb_mul', param_u3, i, True)
      gen_func('sqrT', 'void', arg_p2, 'mclb_sqr', param_u2, i, True)
#      gen_func('mulLowT', 'void', arg_p3, 'mclb_mulLow', param_u3, i, True)
    print('#endif // #if MCL_SIZEOF_UNIT == 4')
    print('#endif // #if MCL_BINT_ASM == 1')
    print(f'''#if MCL_SIZEOF_UNIT == 8
	#define MCL_BINT_ADD_N {addN64}
	#define MCL_BINT_MUL_N {N64}
#else
	#define MCL_BINT_ADD_N {addN}
	#define MCL_BINT_MUL_N {N}
#endif''')
    gen_switch('add', 'Unit', arg_p3, param_u3, addN, addN64)
    gen_switch('sub', 'Unit', arg_p3, param_u3, addN, addN64)
    gen_switch('addNF', 'void', arg_p3, param_u3, addN, addN64)
    gen_switch('subNF', 'Unit', arg_p3, param_u3, addN, addN64)
    gen_switch('mulUnit', 'Unit', arg_p2u, param_u3, N, N64, True)
    gen_switch('mulUnitAdd', 'Unit', arg_p2u, param_u3, N, N64, True)
    gen_switch('mul', 'void', arg_p3, param_u3, N, N64, True)
    gen_switch('sqr', 'void', arg_p2, param_u2, N, N64, True)
  elif opt.out == 'switch':
    print('#if MCL_BINT_ASM != 1')
    gen_inst('addT', 'Unit', arg_p3, addN, addN64)
    gen_inst('subT', 'Unit', arg_p3, addN, addN64)
    gen_inst('addNFT', 'void', arg_p3, addN, addN64)
    gen_inst('subNFT', 'Unit', arg_p3, addN, addN64)
    gen_inst('mulUnitT', 'Unit', arg_p2u, N, N64)
    gen_inst('mulUnitAddT', 'Unit', arg_p2u, N, N64)
    gen_inst('mulT', 'void', arg_p3, N, N64)
    gen_inst('sqrT', 'void', arg_p2, N, N64)
#    gen_inst('mulLowT', 'void', arg_p3, N, N64)
    print('#endif // MCL_BINT_ASM != 1')
    gen_disable(N64)
    gen_mul_slow(N64)
    gen_sqr_slow(N64)
  else:
    print('err : bad out', out)

if __name__ == '__main__':
  main()
