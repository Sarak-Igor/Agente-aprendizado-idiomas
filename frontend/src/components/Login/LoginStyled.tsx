import React, { useState } from 'react';
import styled, { keyframes } from 'styled-components';
import {
  TextField,
  Button,
  Alert,
  CircularProgress,
  IconButton,
  InputAdornment,
  Box,
  Typography,
  Container
} from '@mui/material';
import { Visibility, VisibilityOff, Lock, Person } from '@mui/icons-material';
import { Cpu, Shield, Zap } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate, Link as RouterLink } from 'react-router-dom';

// --- Animations ---
const float = keyframes`
  0% { transform: translateY(0px); }
  50% { transform: translateY(-15px); }
  100% { transform: translateY(0px); }
`;

const fadeIn = keyframes`
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
`;

// --- Styled Components ---

const SplitLayout = styled.div`
  display: flex;
  min-height: 100vh;
  width: 100%;
  overflow: hidden;
  background: #020617;
`;

const HeroSection = styled.div`
  flex: 1.2;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  position: relative;
  background: radial-gradient(circle at center, #1e293b 0%, #0f172a 100%);
  color: white;
  padding: 4rem;
  border-right: 1px solid rgba(255, 255, 255, 0.05);

  @media (max-width: 900px) {
    display: none;
  }
`;

const FormSection = styled.div`
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #020617;
  padding: 2rem;
  position: relative;
`;

const IconWrapper = styled.div`
  width: 100px;
  height: 100px;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  border-radius: 24px;
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 2.5rem;
  box-shadow: 0 0 40px rgba(59, 130, 246, 0.4);
  animation: ${float} 6s ease-in-out infinite;
`;

const HeroTitle = styled.h1`
  font-size: 4rem;
  font-weight: 900;
  margin: 0;
  letter-spacing: -2px;
  background: linear-gradient(135deg, #60a5fa 0%, #2563eb 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  text-transform: uppercase;
`;

const HeroSubtitle = styled.p`
  color: #94a3b8;
  font-size: 1.25rem;
  max-width: 450px;
  text-align: center;
  line-height: 1.6;
  margin-top: 1.5rem;
  animation: ${fadeIn} 1s ease-out;
`;

const BadgeRow = styled.div`
  display: flex;
  gap: 1rem;
  margin-top: 3rem;
`;

const Badge = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 100px;
  color: #94a3b8;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;

  svg {
    width: 14px;
    height: 14px;
    color: #3b82f6;
  }
`;

const FormWrapper = styled.div`
  width: 100%;
  max-width: 400px;
  animation: ${fadeIn} 0.8s ease-out;
`;

const StyledTextField = styled(TextField)`
  && {
    margin-bottom: 1.5rem;
    
    .MuiInputLabel-root {
      color: #64748b;
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1px;
      transform: translate(0, -20px) scale(1);
    }
    
    .MuiOutlinedInput-root {
      background: #0f172a;
      border-radius: 12px;
      color: white;
      transition: all 0.2s;
      
      fieldset {
        border-color: rgba(255, 255, 255, 0.05);
      }
      
      &:hover fieldset {
        border-color: rgba(59, 130, 246, 0.3);
      }
      
      &.Mui-focused fieldset {
        border-color: #3b82f6;
      }
    }
    
    .MuiInputAdornment-root svg {
      color: #475569;
    }
  }
`;

const LoginButton = styled(Button)`
  && {
    margin-top: 1rem;
    padding: 14px;
    border-radius: 12px;
    background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
    color: white;
    font-weight: 700;
    font-size: 1rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    box-shadow: 0 4px 20px rgba(59, 130, 246, 0.3);
    transition: all 0.3s;
    
    &:hover {
      background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
      transform: translateY(-2px);
      box-shadow: 0 6px 25px rgba(59, 130, 246, 0.4);
    }
  }
`;

const TestLoginButton = styled(Button)`
  && {
    margin-top: 1rem !important;
    padding: 10px !important;
    border-radius: 12px !important;
    border: 1px solid rgba(59, 130, 246, 0.3) !important;
    color: #3b82f6 !important;
    font-weight: 600 !important;
    text-transform: none !important;
    transition: all 0.3s !important;
    
    &:hover {
      background: rgba(59, 130, 246, 0.05) !important;
      border-color: #3b82f6 !important;
    }
  }
`;

const FooterLink = styled(RouterLink)`
  color: #3b82f6;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.2s;
  
  &:hover {
    color: #60a5fa;
    text-decoration: underline;
  }
`;

// --- Component ---

export const LoginStyled = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(email, password, false);
      navigate('/app');
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Credenciais inválidas.';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleTestLogin = () => {
    setEmail('usuario@teste.com');
    setPassword('Teste1234');
  };

  return (
    <SplitLayout>
      {/* Left Side: Hero */}
      <HeroSection>
        <IconWrapper>
          <Cpu size={48} color="white" />
        </IconWrapper>
        <HeroTitle>Sarak</HeroTitle>
        <HeroSubtitle>
          agentes e idiomas
        </HeroSubtitle>
        <BadgeRow>
          <Badge><Shield /> Seguro</Badge>
          <Badge><Zap /> Neural</Badge>
        </BadgeRow>
      </HeroSection>

      {/* Right Side: Form */}
      <FormSection>
        <FormWrapper>
          <Box mb={5}>
            <Typography variant="h4" sx={{ color: 'white', fontWeight: 800, mb: 1 }}>
              Login do Sistema
            </Typography>
            <Typography variant="body2" sx={{ color: '#64748b' }}>
              Insira suas credenciais de acesso para continuar.
            </Typography>
          </Box>

          {error && (
            <Alert severity="error" sx={{ mb: 3, borderRadius: '12px', background: 'rgba(239, 68, 68, 0.1)', color: '#f87171', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
              {error}
            </Alert>
          )}

          <form onSubmit={handleSubmit}>
            <StyledTextField
              fullWidth
              label="Usuário"
              placeholder="Digite seu usuário"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Person />
                  </InputAdornment>
                ),
              }}
            />

            <StyledTextField
              fullWidth
              label="Senha"
              type={showPassword ? 'text' : 'password'}
              placeholder="********"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Lock />
                  </InputAdornment>
                ),
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton onClick={() => setShowPassword(!showPassword)} sx={{ color: '#475569' }}>
                      {showPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />

            <Box sx={{ textAlign: 'right', mb: 3 }}>
              <FooterLink to="#" style={{ fontSize: '0.75rem', fontWeight: 600 }}>Esquecceu?</FooterLink>
            </Box>

            <LoginButton
              fullWidth
              variant="contained"
              type="submit"
              disabled={loading}
            >
              {loading ? <CircularProgress size={24} color="inherit" /> : 'Acessar Sistema >'}
            </LoginButton>

            <TestLoginButton
              fullWidth
              variant="outlined"
              onClick={handleTestLogin}
              disabled={loading}
            >
              Entrar como usuário teste
            </TestLoginButton>

            <Box mt={4} textAlign="center">
              <Typography variant="body2" sx={{ color: '#64748b' }}>
                Não tem uma conta? <FooterLink to="/register">Solicitar acesso</FooterLink>
              </Typography>
            </Box>
          </form>
        </FormWrapper>
      </FormSection>
    </SplitLayout>
  );
};
