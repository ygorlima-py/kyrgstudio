import { z } from 'zod'

const MAX_EMAIL_LENGTH = 320
const MIN_PASSWORD_LENGTH = 8
const MAX_PASSWORD_LENGTH = 128
const MAX_NAME_LENGTH = 255

const emailSchema = z
  .string()
  .trim()
  .min(1, 'Email is required.')
  .max(MAX_EMAIL_LENGTH, 'Email is too long.')
  .pipe(z.email('Enter a valid email address.'))
  .transform((email) => email.toLowerCase())

const passwordSchema = z
  .string()
  .min(MIN_PASSWORD_LENGTH, `Password must contain at least ${MIN_PASSWORD_LENGTH} characters.`)
  .max(MAX_PASSWORD_LENGTH, `Password must contain at most ${MAX_PASSWORD_LENGTH} characters.`)

const optionalNameSchema = z
  .string()
  .trim()
  .max(MAX_NAME_LENGTH, 'Name is too long.')
  .transform((name) => (name.length > 0 ? name : undefined))

export const loginFormSchema = z.object({
  email: emailSchema,
  password: passwordSchema,
})

export const registerFormSchema = z
  .object({
    name: optionalNameSchema,
    email: emailSchema,
    password: passwordSchema,
    confirmPassword: passwordSchema,
  })
  .refine((form) => form.password === form.confirmPassword, {
    message: 'Passwords do not match.',
    path: ['confirmPassword'],
  })

export type LoginFormInput = z.input<typeof loginFormSchema>
export type LoginFormData = z.output<typeof loginFormSchema>

export type RegisterFormInput = z.input<typeof registerFormSchema>
export type RegisterFormData = z.output<typeof registerFormSchema>
