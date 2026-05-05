package com.example.backend.repository;

import com.example.backend.entity.Autobiography;
import com.example.backend.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface AutobiographyRepository extends JpaRepository<Autobiography, Long> {
    List<Autobiography> findByUserOrderByCreatedAtDesc(User user);
}
