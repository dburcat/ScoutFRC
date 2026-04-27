import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '../test-utils'

// Create a simple test component
const SimpleButton = ({ onClick, children }: any) => (
  <button onClick={onClick}>{children}</button>
)

describe('Basic Component Tests', () => {
  it('renders a button component', () => {
    const handleClick = vi.fn()
    render(<SimpleButton onClick={handleClick}>Click Me</SimpleButton>)
    
    const button = screen.getByRole('button', { name: /click me/i })
    expect(button).toBeInTheDocument()
  })

  it('calls onClick handler when button is clicked', () => {
    const handleClick = vi.fn()
    const { getByRole } = render(
      <SimpleButton onClick={handleClick}>Click Me</SimpleButton>
    )
    
    const button = getByRole('button')
    button.click()
    expect(handleClick).toHaveBeenCalledOnce()
  })

  it('renders text content correctly', () => {
    render(<SimpleButton>Test Text</SimpleButton>)
    expect(screen.getByText('Test Text')).toBeInTheDocument()
  })
})

describe('Navigation Components', () => {
  const NavLink = ({ to, children }: any) => (
    <a href={to}>{children}</a>
  )

  it('renders navigation link', () => {
    render(<NavLink to="/events">Events</NavLink>)
    const link = screen.getByRole('link', { name: /events/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', '/events')
  })

  it('has correct href attribute', () => {
    render(<NavLink to="/teams">Teams</NavLink>)
    const link = screen.getByRole('link', { name: /teams/i })
    expect(link.getAttribute('href')).toBe('/teams')
  })
})

describe('Form Components', () => {
  const TextInput = ({ label, value, onChange }: any) => (
    <div>
      <label>{label}</label>
      <input value={value} onChange={onChange} />
    </div>
  )

  it('renders input with label', () => {
    render(<TextInput label="Search" value="" onChange={() => {}} />)
    expect(screen.getByText('Search')).toBeInTheDocument()
    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  it('handles input change', () => {
    const handleChange = vi.fn()
    const { getByRole } = render(
      <TextInput label="Search" value="" onChange={handleChange} />
    )
    
    const input = getByRole('textbox') as HTMLInputElement
    input.value = 'test'
    input.dispatchEvent(new Event('change', { bubbles: true }))
    expect(handleChange).toHaveBeenCalled()
  })
})

describe('Display Components', () => {
  const Card = ({ title, children }: any) => (
    <div className="card">
      <h3>{title}</h3>
      <div>{children}</div>
    </div>
  )

  it('renders card with title', () => {
    render(<Card title="Test Card">Content</Card>)
    expect(screen.getByText('Test Card')).toBeInTheDocument()
    expect(screen.getByText('Content')).toBeInTheDocument()
  })

  it('displays children content', () => {
    render(
      <Card title="Card">
        <p>Test paragraph</p>
      </Card>
    )
    expect(screen.getByText('Test paragraph')).toBeInTheDocument()
  })
})
