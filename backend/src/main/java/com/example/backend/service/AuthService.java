package com.example.backend.service;

import com.example.backend.dto.SignUpRequest;
import com.example.backend.entity.User;
import com.example.backend.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class AuthService {

  private final UserRepository userRepository;
  private final BCryptPasswordEncoder passwordEncoder;

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
}
