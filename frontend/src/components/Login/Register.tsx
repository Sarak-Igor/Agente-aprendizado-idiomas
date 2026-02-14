import React, { useState } from 'react';
import styled, { keyframes } from 'styled-components';
import {
  Box,
  TextField,
  Button,
  Typography,
  Alert,
  CircularProgress,
  IconButton,
  InputAdornment,
  MenuItem,
  Container
} from '@mui/material';
import { Visibility, VisibilityOff, Lock, Person, Email, Language } from '@mui/icons-material';
import { Cpu } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate, Link as RouterLink } from 'react-router-dom';

const LANGUAGES = [
  { code: 'pt', name: 'Português' },
  { code: 'en', name: 'Inglês' },
  { code: 'es', name: 'Espanhol' },
  { code: 'fr', name: 'Francês' },
  { code: 'de', name: 'Alemão' },
  { code: 'it', name: 'Italiano' },
  { code: 'ja', name: 'Japonês' },
  { code: 'ko', name: 'Coreano' },
  { code: 'zh', name: 'Chinês' },
  { code: 'ru', name: 'Russo' },
];

const fadeIn = keyframes`
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
`;

const PageWrapper = styled.div`
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at center, #0f172a 0%, #020617 100%);
  padding: 2rem;
`;

const RegisterCard = styled.div`
  width: 100%;
  max-width: 550px;
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 24px;
  padding: 3rem;
  animation: ${fadeIn} 0.8s ease-out;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
`;

const Title = styled.h1`
  font-size: 2.5rem;
  font-weight: 800;
  margin: 0;
  background: linear-gradient(135deg, #60a5fa 0%, #2563eb 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  text-align: center;
`;

const StyledTextField = styled(TextField)`
  && {
    margin-bottom: 1.25rem;
    
    .MuiInputLabel-root {
      color: #64748b;
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1px;
    }
    
    .MuiOutlinedInput-root {
      background: #020617;
      border-radius: 12px;
      color: white;
      
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
    
    .MuiSelect-icon {
      color: #475569;
    }
  }
`;

const ActionButton = styled(Button)`
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
    
    &:hover {
      background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
      transform: translateY(-2px);
    }
  }
`;

const StyledLink = styled(RouterLink)`
  color: #3b82f6;
  text-decoration: none;
  font-weight: 600;
  &:hover {
    text-decoration: underline;
  }
`;

export const Register = () => {
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [nativeLanguage, setNativeLanguage] = useState('pt');
  const [learningLanguage, setLearningLanguage] = useState('en');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (nativeLanguage === learningLanguage) {
      setError('Os idiomas devem ser diferentes.');
      return;
    }

    try {
      setLoading(true);
      await register(email, username, nativeLanguage, learningLanguage, password);
      navigate('/app');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao criar conta.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageWrapper>
      <RegisterCard>
        <Box textAlign="center" mb={4}>
          <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
            <Cpu size={40} color="#3b82f6" />
          </Box>
          <Title>Sarak</Title>
          <Typography variant="body2" sx={{ color: '#64748b', mt: 1 }}>
            Cadastre-se para começar sua jornada
          </Typography>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 3, borderRadius: '12px', bgcolor: 'rgba(239,68,68,0.1)', color: '#f87171' }}>
            {error}
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <StyledTextField
            fullWidth
            label="E-mail"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            InputProps={{ startAdornment: <InputAdornment position="start"><Email /></InputAdornment> }}
          />

          <StyledTextField
            fullWidth
            label="Usuário"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            InputProps={{ startAdornment: <InputAdornment position="start"><Person /></InputAdornment> }}
          />

          <Box sx={{ display: 'flex', gap: 2, mb: 1 }}>
            <StyledTextField
              select
              fullWidth
              label="Nativo"
              value={nativeLanguage}
              onChange={(e) => setNativeLanguage(e.target.value)}
              InputProps={{ startAdornment: <InputAdornment position="start"><Language /></InputAdornment> }}
            >
              {LANGUAGES.map((l) => <MenuItem key={l.code} value={l.code}>{l.name}</MenuItem>)}
            </StyledTextField>
            <StyledTextField
              select
              fullWidth
              label="Aprender"
              value={learningLanguage}
              onChange={(e) => setLearningLanguage(e.target.value)}
              InputProps={{ startAdornment: <InputAdornment position="start"><Language /></InputAdornment> }}
            >
              {LANGUAGES.map((l) => <MenuItem key={l.code} value={l.code}>{l.name}</MenuItem>)}
            </StyledTextField>
          </Box>

          <StyledTextField
            fullWidth
            label="Senha"
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            InputProps={{
              startAdornment: <InputAdornment position="start"><Lock /></InputAdornment>,
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton onClick={() => setShowPassword(!showPassword)} sx={{ color: '#475569' }}>
                    {showPassword ? <VisibilityOff /> : <Visibility />}
                  </IconButton>
                </InputAdornment>
              )
            }}
          />

          <ActionButton
            fullWidth
            variant="contained"
            type="submit"
            disabled={loading}
          >
            {loading ? <CircularProgress size={24} color="inherit" /> : 'Criar Conta'}
          </ActionButton>

          <Box mt={3} textAlign="center">
            <Typography variant="body2" sx={{ color: '#64748b' }}>
              Já possui acesso? <StyledLink to="/login">Fazer login</StyledLink>
            </Typography>
          </Box>
        </form>
      </RegisterCard>
    </PageWrapper>
  );
};
