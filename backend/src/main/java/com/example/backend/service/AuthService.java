package com.example.backend.service;

import com.example.backend.dto.SignInRequest;
import com.example.backend.dto.SignUpRequest;
import com.example.backend.entity.User;
import com.example.backend.repository.UserRepository;
import com.example.backend.security.JwtProvider;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class AuthService {

  private final UserRepository userRepository;
  private final BCryptPasswordEncoder passwordEncoder;
  private final JwtProvider jwtProvider;

  @Transactional
  public void signUp(SignUpRequest request) {
    userRepository.findByEmail(request.getEmail())
      .ifPresent(u -> {
        throw new RuntimeException("이미 존재하는 이메일입니다.");
      });

    String encodedPassword = passwordEncoder.encode(request.getPassword());
    User user = new User(request.getEmail(), encodedPassword, request.getName());
    userRepository.save(user);
  }

  @Transactional(readOnly = true)
  public String signIn(SignInRequest request) {
    User user = userRepository.findByEmail(request.getEmail())
      .orElseThrow(() -> new RuntimeException("가입되지 않은 이메일입니다."));

    if (!passwordEncoder.matches(request.getPassword(), user.getPassword())) {
      throw new RuntimeException("비밀번호가 일치하지 않습니다.");
    }
    
    return jwtProvider.createToken(user.getEmail());
  }
}
