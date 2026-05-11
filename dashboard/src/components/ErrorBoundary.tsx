/** Error boundary — catches render errors and shows a styled fallback. */

import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  message: string;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, message: '' };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div
          role="alert"
          style={{
            backgroundColor: '#FDEAEA',
            border: '1px solid #E03448',
            borderRadius: 10,
            padding: '20px 24px',
          }}
        >
          <div
            style={{
              fontFamily: 'var(--fb)',
              fontSize: 10,
              fontWeight: 700,
              letterSpacing: '2px',
              textTransform: 'uppercase',
              color: '#7A1020',
              marginBottom: 6,
            }}
          >
            Something went wrong
          </div>
          <p
            style={{
              fontFamily: 'var(--fb)',
              fontSize: 13,
              color: '#7A1020',
              margin: 0,
            }}
          >
            {this.state.message || 'An unexpected error occurred. Please refresh the page.'}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, message: '' })}
            style={{
              marginTop: 12,
              background: 'none',
              border: '1px solid #E03448',
              borderRadius: 6,
              color: '#7A1020',
              cursor: 'pointer',
              fontFamily: 'var(--fb)',
              fontSize: 10,
              letterSpacing: '2px',
              textTransform: 'uppercase',
              padding: '5px 12px',
            }}
          >
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
