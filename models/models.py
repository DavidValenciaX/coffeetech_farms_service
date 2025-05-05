from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class FarmStates(Base):
    __tablename__ = 'farm_states'
    farm_state_id = Column(Integer, primary_key=True)
    name = Column(String(45), nullable=False, unique=True)
    farms = relationship("Farms", back_populates="state")

class Farms(Base):
    __tablename__ = 'farms'

    farm_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    area = Column(Numeric(10, 2), nullable=False)
    area_unit_id = Column(Integer, ForeignKey('area_units.area_unit_id'), nullable=False)
    farm_state_id = Column(Integer, ForeignKey('farm_states.farm_state_id'), nullable=False)
    __table_args__ = (CheckConstraint('area > 0'),)

    # Relaciones
    area_unit = relationship("AreaUnits", back_populates="farms")
    state = relationship("FarmStates", back_populates="farms")
    user_roles_farms = relationship('UserRoleFarm', back_populates='farm', cascade="all, delete-orphan")
    plots = relationship("Plots", back_populates="farm", cascade="all, delete-orphan")

class PlotStates(Base):
    __tablename__ = 'plot_states'
    plot_state_id = Column(Integer, primary_key=True)
    name = Column(String(45), nullable=False, unique=True)
    plots = relationship("Plots", back_populates="state")

class Plots(Base):
    __tablename__ = 'plots'
    __table_args__ = (
        UniqueConstraint('name', 'farm_id'),
        CheckConstraint('longitude BETWEEN -180 AND 180'),
        CheckConstraint('latitude BETWEEN -90 AND 90'),
        CheckConstraint('altitude >= 0 AND altitude <= 3000'),
    )

    plot_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    longitude = Column(Numeric(11, 8), nullable=True)
    latitude = Column(Numeric(11, 8), nullable=True)
    altitude = Column(Numeric(10, 2), nullable=True)
    coffee_variety_id = Column(Integer, ForeignKey('coffee_varieties.coffee_variety_id'), nullable=False)
    farm_id = Column(Integer, ForeignKey('farms.farm_id', ondelete='CASCADE'), nullable=False)
    plot_state_id = Column(Integer, ForeignKey('plot_states.plot_state_id'), nullable=False)

    # Relaciones
    farm = relationship("Farms", back_populates="plots")
    coffee_variety = relationship("CoffeeVarieties", back_populates="plots")
    state = relationship("PlotStates", back_populates="plots")

class CoffeeVarieties(Base):
    __tablename__ = 'coffee_varieties'

    coffee_variety_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)

    # Relaciones
    plots = relationship("Plots", back_populates="coffee_variety")

class AreaUnits(Base):
    __tablename__ = 'area_units'

    area_unit_id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    abbreviation = Column(String(10), nullable=False, unique=True)

    # Relaciones
    farms = relationship("Farms", back_populates="area_unit")

class UserRoleFarmStates(Base):
    __tablename__ = 'user_role_farm_states'
    user_role_farm_state_id = Column(Integer, primary_key=True)
    name = Column(String(45), nullable=False, unique=True)
    user_role_farm = relationship("UserRoleFarm", back_populates="state")

class UserRoleFarm(Base):
    __tablename__ = 'user_role_farm'

    user_role_farm_id = Column(Integer, primary_key=True)
    user_role_id = Column(Integer, nullable=False)
    farm_id = Column(Integer, ForeignKey('farms.farm_id', ondelete='CASCADE'), nullable=False)
    user_role_farm_state_id = Column(Integer, ForeignKey('user_role_farm_states.user_role_farm_state_id'), nullable=False)
    __table_args__ = (UniqueConstraint('user_role_id', 'farm_id'),)

    # Relaciones
    farm = relationship('Farms', back_populates='user_roles_farms')
    state = relationship('UserRoleFarmStates', back_populates='user_role_farm')
