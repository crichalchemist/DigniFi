import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export function AppHeader() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleSignOut = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <header className="app-header" role="banner">
      <div className="app-header-inner">
        <Link to="/intake" className="app-header-wordmark" aria-label="DigniFi — go to intake">
          DigniFi
        </Link>
        <button className="app-header-signout" onClick={handleSignOut} type="button">
          Sign out
        </button>
      </div>
    </header>
  );
}

export default AppHeader;
